# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A calculator a DEFINE-only attribute or command holds cannot change in EVENTS.

The holder is fixed after DEFINE, so an EVENTS statement setting an attribute
of the calculator it holds, directly or through an expression, is rejected
when the deck is read. A calculator held only where EVENTS may change the
holder, or only by a node the prune removes, stays free.
"""

from __future__ import annotations

import pytest

from navigate.exceptions import AttributeAssignmentError

# the Fleet is a top-level node, so everything down to the Converter survives
# the unreachable-node prune (see the conftest module docstring); a Converter's
# PowerCapacity is DEFINE-only and its Efficiency is not
FLEET = """
Fleet "fleet" {{
    Vessels = [Vessel("vessel")]
    InterFuelSensitivity = 0.5
    IntraFuelSensitivity = 0.5
    InitialVessels = 100
}}
Vessel "vessel" {{
    PowerSystem = PowerSystem("ps")
    Route = Route("route")
    NominalCapacity = 8000
    Tanks = [Tank("tank")]
}}
PowerSystem "ps" {{
    Propulsion = Converter("propulsion")
    Electrical = Converter("electrical")
    Heat = Converter("heat")
}}
Converter "propulsion" {{
    PowerCapacity = {power_capacity}
    Efficiency = {efficiency}
    MainFuelTypes = OIL
}}
Converter "electrical" {{
    PowerCapacity = 10
    Efficiency = 0.5
    MainFuelTypes = OIL
}}
Copy Converter "electrical" "heat"
Tank "tank" {{
    FuelTypes = OIL
    Size = 9000
}}
Route "route" {{
    RouteType = REGIONAL_TRIP
    Ports = [Port("port")]
    TimeAtSea = 0.75
    ConditionDistribution = [1.0]
    Speeds = [10]
}}
Port "port" {{ }}
"""
VARIABLES = 'Variable "p" { Value = 1.0 }\nVariable "q" { Value = 1.0 }\n'
# an Emission is a top-level node too, and its GlobalWarmingPotential is
# DEFINE-only
EMISSION = 'Emission "e" {{ GlobalWarmingPotential = {value} }}\n'


def _fleet(power_capacity="50", efficiency="0.5"):
    return FLEET.format(power_capacity=power_capacity, efficiency=efficiency)


def _events(target):
    return f"""
Start
Date "01-01-2027"
Variable "{target}" {{ Value = 0.4 }}
End
"""


def _pinned_error(calculator, holder, holder_input):
    return (
        rf"{calculator} does not allow setting attribute 'Value' in 'EVENTS', as "
        rf"{holder} holds it in '{holder_input}', which is DEFINE-only\.$"
    )


@pytest.mark.parametrize(
    ("power_capacity", "target"),
    [
        ('Variable("p")', "p"),
        ('<Variable("p") + Variable("q")>', "q"),
    ],
    ids=["reference", "expression"],
)
def test_a_define_only_attribute_pins_the_calculator_it_holds(
    read_deck, power_capacity, target
):
    define = VARIABLES + _fleet(power_capacity=power_capacity)

    with pytest.raises(
        AttributeAssignmentError,
        match=_pinned_error(
            rf'Variable\("{target}"\)', r'Converter\("propulsion"\)', "PowerCapacity"
        ),
    ):
        read_deck(define, events=_events(target))


def test_the_error_names_the_event_line(read_deck):
    define = VARIABLES + _fleet(power_capacity='Variable("p")')

    with pytest.raises(AttributeAssignmentError, match=r"events\.inc', line 4: "):
        read_deck(define, events=_events("p"))


def test_a_define_only_command_pins_the_calculator_it_is_given(read_deck):
    define = VARIABLES + (
        'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'
        'Fuel "oil" {\n'
        "    FuelType = OIL\n"
        "    LowerHeatingValue = 41.2\n"
        "    MassDensity = 0.9\n"
        '    set_ttw("co2", Variable("p"))\n'
        "}\n"
    )

    with pytest.raises(
        AttributeAssignmentError,
        match=_pinned_error(r'Variable\("p"\)', r'Fuel\("oil"\)', "set_ttw"),
    ):
        read_deck(define, events=_events("p"))


def test_a_wildcard_target_matching_a_pinned_calculator_is_rejected(read_deck):
    # "q" is free, so only the match on "p" can reject the statement
    define = VARIABLES + _fleet(
        power_capacity='Variable("p")', efficiency='Variable("q")'
    )

    with pytest.raises(AttributeAssignmentError, match=r'Variable\("p"\) does not'):
        read_deck(define, events=_events("*"))


def test_a_calculator_held_only_by_an_attribute_events_may_change_is_free(
    read_deck,
):
    define = VARIABLES + _fleet(efficiency='Variable("p")')

    read_deck(define, events=_events("p"))


def test_a_holder_the_prune_removes_pins_nothing(read_deck):
    # nothing reaches the spare Converter, so only the Efficiency it is free in
    # keeps "p" in the run
    define = (
        VARIABLES + _fleet(efficiency='Variable("p")') + 'Converter "spare" {\n'
        '    PowerCapacity = Variable("p")\n'
        "    Efficiency = 0.5\n"
        "    MainFuelTypes = OIL\n"
        "}\n"
    )

    parser = read_deck(define, events=_events("p"))

    assert "spare" not in parser.nodes.converters


class TestCopy:
    def test_a_copy_of_a_pinned_calculator_is_free(self, read_deck):
        define = (
            VARIABLES
            + 'Copy Variable "p" "r"\n'
            + _fleet(power_capacity='Variable("p")', efficiency='Variable("r")')
        )

        read_deck(define, events=_events("r"))

    def test_a_placeholder_a_copy_fills_stays_pinned(self, read_deck):
        # the Emission names "r" before the Copy declares it
        define = (
            EMISSION.format(value='Variable("r")')
            + VARIABLES
            + 'Copy Variable "p" "r"\n'
        )

        with pytest.raises(
            AttributeAssignmentError,
            match=_pinned_error(
                r'Variable\("r"\)', r'Emission\("e"\)', "GlobalWarmingPotential"
            ),
        ):
            read_deck(define, events=_events("r"))

    def test_a_copied_holder_pins_through_its_own_expression(self, tmp_path, read_deck):
        # the source is pulled from the library and leaves the registry after
        # the copy, so only the expression the copy holds names "p"
        library = tmp_path / "data" / "defaults"
        for branch in ("user", "installation"):
            (library / branch / "Emission").mkdir(parents=True)
        (library / "installation" / "Emission" / "lib.inc").write_text(
            EMISSION.replace('"e"', '"lib"').format(value='<Variable("p")>')
        )
        define = VARIABLES + 'Copy Emission "lib" "e"\n'

        with pytest.raises(
            AttributeAssignmentError,
            match=_pinned_error(
                r'Variable\("p"\)', r'Emission\("e"\)', "GlobalWarmingPotential"
            ),
        ):
            read_deck(define, events=_events("p"))
