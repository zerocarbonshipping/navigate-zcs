# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A calculator a DEFINE-only attribute or command holds cannot change in EVENTS.

The holder is fixed after DEFINE, so an EVENTS statement setting an attribute
of the calculator it holds, directly or through an expression, is rejected
when the deck is read. A calculator held only where EVENTS may change the
holder, written over before DEFINE ends, copied, or held only by a node the
prune removes, stays free.
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import fleet, variable
from navigate.exceptions import AttributeAssignmentError

VARIABLES = variable("p", Value=1.0) + variable("q", Value=1.0)
CO2 = 'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'
N2O = 'Emission "n2o" { GlobalWarmingPotential = 1.0 }\n'


def _fuel(commands):
    return f"""
Fuel "oil" {{
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
    {commands}
}}
"""


def _events(target):
    return f'Start\nDate "01-01-2027"\nVariable "{target}" {{ Value = 0.4 }}\nEnd\n'


def _pinned(calculator, holder, holder_input):
    return (
        rf"{calculator} does not allow setting attribute 'Value' in 'EVENTS', as "
        rf"{holder} holds it in '{holder_input}', which is DEFINE-only\.$"
    )


FUEL_PINS_P = _pinned(r'Variable\("p"\)', r'Fuel\("oil"\)', "set_ttw")


# input:    | DEFINE: Converter "propulsion" { PowerCapacity = Variable("p") }
#           | EVENTS: Variable "p" { Value = 0.4 }
# expected: -> AttributeAssignmentError "Variable("p") does not allow setting
#              attribute 'Value' in 'EVENTS', as Converter("propulsion") holds
#              it in 'PowerCapacity', which is DEFINE-only."
@pytest.mark.parametrize(
    ("power_capacity", "target"),
    [('Variable("p")', "p"), ('<Variable("p") + Variable("q")>', "q")],
    ids=["reference", "expression"],
)
def test_a_define_only_attribute_pins_the_calculator_it_holds(
    read_deck, power_capacity, target
):
    # a Converter's PowerCapacity is DEFINE-only; the error names the EVENTS
    # line setting the calculator
    define = VARIABLES + fleet(power_capacity=power_capacity)

    with pytest.raises(
        AttributeAssignmentError,
        match=r"events\.inc', line 3: "
        + _pinned(
            rf'Variable\("{target}"\)', r'Converter\("propulsion"\)', "PowerCapacity"
        ),
    ):
        read_deck(define, events=_events(target))


# input:    | DEFINE: Fuel "oil" { ... set_ttw("co2", Variable("p")) }
#           | EVENTS: Variable "p" { Value = 0.4 }
# expected: -> AttributeAssignmentError "Variable("p") does not allow setting
#              ... as Fuel("oil") holds it in 'set_ttw', which is DEFINE-only."
def test_a_define_only_command_pins_the_calculator_it_is_given(read_deck):
    define = VARIABLES + CO2 + _fuel('set_ttw("co2", Variable("p"))')

    with pytest.raises(AttributeAssignmentError, match=FUEL_PINS_P):
        read_deck(define, events=_events("p"))


# input:    | DEFINE: PowerCapacity = Variable("p")  Efficiency = Variable("q")
#           | EVENTS: Variable "*" { Value = 0.4 }
# expected: -> AttributeAssignmentError "Variable("p") does not ..."
#              (only "p" is pinned)
def test_a_wildcard_target_matching_a_pinned_calculator_is_rejected(read_deck):
    # "q" is free, so only the match on "p" can reject the statement
    define = VARIABLES + fleet(
        power_capacity='Variable("p")', efficiency='Variable("q")'
    )

    with pytest.raises(AttributeAssignmentError, match=r'Variable\("p"\) does not'):
        read_deck(define, events=_events("*"))


# input:    | DEFINE: Fuel "oil" { set_ttw("co2", Variable("p"))
#           | set_ttw("co2", 3.1) }
#           | EVENTS: Variable "p" { Value = 0.4 }
# expected: -> the deck reads with no error; nothing holds "p" any more
@pytest.mark.parametrize(
    "commands",
    [
        # the second call writes the entry the first wrote
        'set_ttw("co2", Variable("p"))\n    set_ttw("co2", 3.1)',
        # a wildcard call covering the entry writes it too
        'set_ttw("co2", Variable("p"))\n    set_ttw("*", Variable("q"))',
    ],
    ids=["same_key", "covering_wildcard"],
)
def test_a_command_writing_the_entry_again_frees_the_calculator(read_deck, commands):
    read_deck(VARIABLES + CO2 + N2O + _fuel(commands), events=_events("p"))


# input:    | DEFINE: Fuel "oil" { set_ttw("*", Variable("p"))
#           | set_ttw("co2", Variable("q")) }
#           | EVENTS: Variable "p" { Value = 0.4 }
# expected: -> AttributeAssignmentError: the n2o entry still holds "p"
@pytest.mark.parametrize(
    "commands",
    [
        # the n2o entry the wildcard wrote still holds "p"
        'set_ttw("*", Variable("p"))\n    set_ttw("co2", Variable("q"))',
        # "n2*" does not reach the co2 entry
        'set_ttw("co2", Variable("p"))\n    set_ttw("n2*", Variable("q"))',
    ],
    ids=["narrower_override", "disjoint_wildcard"],
)
def test_a_command_leaves_the_entries_its_keys_do_not_cover_pinned(read_deck, commands):
    with pytest.raises(AttributeAssignmentError, match=FUEL_PINS_P):
        read_deck(VARIABLES + CO2 + N2O + _fuel(commands), events=_events("p"))


# input:    | DEFINE: Converter "propulsion" { Efficiency = Variable("p") }
#           | EVENTS: Variable "p" { Value = 0.4 }
# expected: -> the deck reads with no error (Efficiency may change in EVENTS)
@pytest.mark.parametrize(
    ("define", "target"),
    [
        # Efficiency may change in EVENTS, so it pins nothing
        (VARIABLES + fleet(efficiency='Variable("p")'), "p"),
        # the copy is a new calculator nothing DEFINE-only holds
        (
            VARIABLES
            + 'Copy Variable "p" "r"\n'
            + fleet(power_capacity='Variable("p")', efficiency='Variable("r")'),
            "r",
        ),
        # nothing reaches the spare Converter, so the prune removes its pin
        (
            VARIABLES
            + fleet(efficiency='Variable("p")')
            + 'Converter "spare" {\n    PowerCapacity = Variable("p")\n'
            "    Efficiency = 0.5\n    MainFuelTypes = OIL\n}\n",
            "p",
        ),
    ],
    ids=["events_attribute", "copy", "pruned_holder"],
)
def test_a_calculator_no_surviving_define_only_input_holds_is_free(
    read_deck, define, target
):
    read_deck(define, events=_events(target))


# input:    | DEFINE: Emission "e" { GlobalWarmingPotential = Variable("r") }
#           | Copy Variable "p" "r"
#           | EVENTS: Variable "r" { Value = 0.4 }
# expected: -> AttributeAssignmentError "Variable("r") does not allow setting
#              ... as Emission("e") holds it in 'GlobalWarmingPotential' ..."
def test_a_placeholder_a_copy_fills_stays_pinned(read_deck):
    # the Emission names "r" before the Copy declares it
    define = (
        'Emission "e" { GlobalWarmingPotential = Variable("r") }\n'
        + VARIABLES
        + 'Copy Variable "p" "r"\n'
    )

    with pytest.raises(
        AttributeAssignmentError,
        match=_pinned(r'Variable\("r"\)', r'Emission\("e"\)', "GlobalWarmingPotential"),
    ):
        read_deck(define, events=_events("r"))
