# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The command registry, the arity check, and the enum wildcards of a command.

Every `(node type, command)` entry of `NODE_COMMAND_SECTIONS` is tried in both
sections against the check the parser runs when it queues a command, and
every enum domain of `_WILDCARD_DOMAINS` is expanded from a bare `*` against
its members, written out here. A queued command runs as a `CommandReference`,
which checks the number of arguments against the method before it calls it.
"""

from __future__ import annotations

import inspect
import re

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.report import Report
from navigate.exceptions import CommandError
from navigate.parser._commands import (
    _WILDCARD_DOMAINS,
    NODE_COMMAND_SECTIONS,
    CommandReference,
    check_node_command_is_allowed,
)
from navigate.parser._keywords import (
    GENERAL_NODE_CLASS,
    KEYWORD_SECTIONS,
    NODE_CLASS,
    SECTION_DEFINE,
)
from navigate.parser._lark_parser import SourceLocation

DEFINE = SimulationSectionID.DEFINE
EVENTS = SimulationSectionID.EVENTS

ENTRIES = [
    pytest.param(node_type, command, sections, id=f"{node_type}.{command}")
    for node_type, commands in NODE_COMMAND_SECTIONS.items()
    for command, sections in commands.items()
]

# the DEFINE-only commands of the node types a deck may re-open in EVENTS
EVENTS_REJECTED = [
    pytest.param(node_type, command, id=f"{node_type}.{command}")
    for node_type, commands in NODE_COMMAND_SECTIONS.items()
    for command, sections in commands.items()
    if sections == SECTION_DEFINE and EVENTS in KEYWORD_SECTIONS[node_type]
]

FUEL_TYPES = [
    "AMMONIA",
    "ELECTRICITY",
    "ETHANOL",
    "HYDROGEN",
    "LPG",
    "METHANE",
    "METHANOL",
    "OIL",
]
DEMANDS = ["PROPULSION", "ELECTRICAL", "HEAT"]
PORT_DEMANDS = ["ELECTRICAL", "HEAT"]

# what a bare '*' expands to, per command and argument position
STAR_EXPANSION = {
    ("set_slip_fraction", 0): FUEL_TYPES,
    ("set_consumption_ttw", 0): FUEL_TYPES,
    ("set_operational_saving_sea", 0): DEMANDS,
    ("set_operational_saving_port", 0): PORT_DEMANDS,
    ("set_energy_saving", 0): DEMANDS,
    ("set_external_power", 0): DEMANDS,
    ("set_power_transfer", 0): DEMANDS,
    ("set_power_transfer", 1): DEMANDS,
}


class _Recorder:
    """Stand-in node recording every call of a command with an enum domain."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __str__(self) -> str:
        return "Recorder"

    def set_slip_fraction(self, fuel_type, value):
        self.calls.append((fuel_type, value))

    def set_consumption_ttw(self, fuel_type, emission_name, value):
        self.calls.append((fuel_type, emission_name, value))

    def set_operational_saving_sea(self, energy_type, saving):
        self.calls.append((energy_type, saving))

    def set_operational_saving_port(self, energy_type, saving):
        self.calls.append((energy_type, saving))

    def set_energy_saving(self, energy_type, saving):
        self.calls.append((energy_type, saving))

    def set_external_power(self, energy_type, power):
        self.calls.append((energy_type, power))

    def set_power_transfer(self, power_system_id, energy_id, transfer):
        self.calls.append((power_system_id, energy_id, transfer))

    def set_include_vessel(self, vessel_name, include_vessel):
        self.calls.append((vessel_name, include_vessel))


def _execute(node, command: str, inputs: list) -> None:
    CommandReference(command, inputs, source=SourceLocation("f.inc", 1)).execute(node)


def _calls(command: str, inputs: list) -> list[tuple]:
    recorder = _Recorder()
    _execute(recorder, command, inputs)
    return recorder.calls


# input:    | Fleet "f" { set_newbuild_limit(...) }  /  BunkerOptions { set_x(1) }
# expected: -> every node type has a command table; BunkerOptions and
#              ModelDefinition have none
def test_every_node_type_has_a_registry():
    # a general node takes no command at all
    assert set(NODE_COMMAND_SECTIONS) == set(NODE_CLASS)
    assert not set(NODE_COMMAND_SECTIONS) & set(GENERAL_NODE_CLASS)


# ── the section check, entry by entry ─────────────────────────────────────────


# input:    | e.g. Fleet "f" { set_newbuild_limit(...) }            in EVENTS
#           | and  Fleet "f" { set_initial_technology_share(...) }  in EVENTS
# expected: -> set_newbuild_limit is accepted; set_initial_technology_share
#              -> CommandError "Nodes of type 'Fleet' does not allow use of command
#              'set_initial_technology_share' in 'EVENTS'"
@pytest.mark.parametrize(("node_type", "command", "sections"), ENTRIES)
@pytest.mark.parametrize("section", [DEFINE, EVENTS], ids=["DEFINE", "EVENTS"])
def test_command_section(node_type, command, sections, section):
    if section in sections:
        check_node_command_is_allowed(node_type, command, section)
        return

    message = (
        f"Nodes of type '{node_type}' does not allow use of command '{command}' in "
        f"'{section.name}'"
    )
    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        check_node_command_is_allowed(node_type, command, section)


# input:    | e.g. Port "p" { bogus(1) }
# expected: -> CommandError "Nodes of type 'Port' has no command 'bogus'"
@pytest.mark.parametrize("node_type", NODE_COMMAND_SECTIONS)
def test_node_type_has_no_unknown_command(node_type):
    message = f"Nodes of type '{node_type}' has no command 'bogus'"

    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        check_node_command_is_allowed(node_type, "bogus", DEFINE)


# input:    | Fuel "f" { Set_ttw("co2", 3.2) }
# expected: -> CommandError "... has no command 'Set_ttw'" (only set_ttw is known)
def test_a_command_name_is_case_sensitive():
    with pytest.raises(CommandError, match="has no command 'Set_ttw'"):
        check_node_command_is_allowed("Fuel", "Set_ttw", DEFINE)


# ── the parser runs the check when it queues a command ────────────────────────


# input:    | DEFINE: Fleet "n" { }
#           | EVENTS: Fleet "n" { set_initial_technology_share() }
# expected: -> CommandError "Error in deck file, line 2, include file '.../events.inc',
#              line 2: Nodes of type 'Fleet' does not allow use of command
#              'set_initial_technology_share' in 'EVENTS'."
@pytest.mark.parametrize(("node_type", "command"), EVENTS_REJECTED)
def test_a_define_only_command_in_events_stops_the_deck(
    tmp_path, read_deck, node_type, command
):
    message = (
        f"Error in deck file, line 2, include file '{tmp_path / 'events.inc'}', "
        f"line 2: Nodes of type '{node_type}' does not allow use of command "
        f"'{command}' in 'EVENTS'."
    )

    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        read_deck(
            f'{node_type} "n" {{\n}}\n',
            events=f'{node_type} "n" {{\n    {command}()\n}}\n',
        )


# input:    | Port "p" {
#           |     bogus(1)
#           | }
# expected: -> CommandError "Error in deck file, line 1, include file '.../define.inc',
#              line 6: Nodes of type 'Port' has no command 'bogus'."
def test_an_unknown_command_stops_the_deck(tmp_path, read_deck):
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        "line 6: Nodes of type 'Port' has no command 'bogus'."
    )

    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        read_deck('Port "p" {\n    bogus(1)\n}\n')


# input:    | e.g. ModelDefinition {
#           |          set_x(1)
#           |      }
# expected: -> CommandError "Error in deck file, line 1, include file '.../define.inc',
#              line 6: 'ModelDefinition' does not support commands."
@pytest.mark.parametrize("type_", GENERAL_NODE_CLASS)
def test_a_general_node_takes_no_command(tmp_path, read_deck, type_):
    # ModelDefinition is declared again: the base declaration is re-opened
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        f"line 6: '{type_}' does not support commands."
    )

    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        read_deck(f"{type_} {{\n    set_x(1)\n}}\n")


# ── the number of arguments ───────────────────────────────────────────────────


# input:    | e.g. Fuel "f" { set_ttw("co2") }   (set_ttw takes emission_name and ttw)
# expected: -> CommandError "Fuel("f"): Command 'set_ttw' requires 2 inputs,
#              'emission_name' and 'ttw', but only 1 was given"
#              and set_ttw("co2", 1.0, 2.0) -> "... takes up to 2 inputs,
#              ... but 3 were given"
@pytest.mark.parametrize(
    ("node", "command", "inputs", "message"),
    [
        (
            Fuel("f"),
            "set_ttw",
            ["co2"],
            "Fuel(\"f\"): Command 'set_ttw' requires 2 inputs, 'emission_name' and "
            "'ttw', but only 1 was given",
        ),
        (
            Converter("c"),
            "set_consumption_ttw",
            ["OIL", "co2"],
            "Converter(\"c\"): Command 'set_consumption_ttw' requires 3 inputs, "
            "'fuel_type', 'emission_name', and 'value', but only 2 were given",
        ),
        (
            Fuel("f"),
            "set_ttw",
            ["co2", 1.0, 2.0],
            "Fuel(\"f\"): Command 'set_ttw' takes up to 2 inputs, 'emission_name' and "
            "'ttw', but 3 were given",
        ),
        (
            Converter("c"),
            "set_consumption_ttw",
            ["OIL", "co2", 1.0, 2.0],
            "Converter(\"c\"): Command 'set_consumption_ttw' takes up to 3 inputs, "
            "'fuel_type', 'emission_name', and 'value', but 4 were given",
        ),
        (
            # an optional argument counts towards the most a command takes
            Report("r"),
            "add_property",
            ["a", "b", "c"],
            "Report(\"r\"): Command 'add_property' takes up to 2 inputs, 'attribute' "
            "and 'reduce', but 3 were given",
        ),
    ],
    ids=[
        "too_few_of_two",
        "too_few_of_three",
        "too_many_of_two",
        "too_many_of_three",
        "too_many_with_an_optional",
    ],
)
def test_a_command_with_the_wrong_number_of_arguments(node, command, inputs, message):
    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        _execute(node, command, inputs)


# input:    | Fuel "f" {
#           |     ...
#           |     set_ttw("co2")
#           | }
# expected: -> CommandError "Error in deck file, line 1, include file '.../define.inc',
#              line 9: Fuel("f"): Command 'set_ttw' requires 2 inputs, ..."
def test_an_arity_error_in_a_deck_is_located(tmp_path, read_deck):
    # Fuel is a root, so its queued command runs in the DEFINE pass
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        "line 9: Fuel(\"f\"): Command 'set_ttw' requires 2 inputs, 'emission_name' "
        "and 'ttw', but only 1 was given."
    )

    with pytest.raises(CommandError, match=f"^{re.escape(message)}$"):
        read_deck(
            'Fuel "f" {\n    FuelType = OIL\n    LowerHeatingValue = 40\n'
            '    MassDensity = 900\n    set_ttw("co2")\n}\n'
        )


# ── enum wildcards ────────────────────────────────────────────────────────────


# input:    | e.g. Converter "c" { set_slip_fraction(M*, 0.03) }
# expected: -> set_slip_fraction is a registered command, and the enum argument
#              that a wildcard may expand (fuel type) comes before the value
@pytest.mark.parametrize("command", _WILDCARD_DOMAINS)
def test_a_wildcard_domain_belongs_to_a_registered_command(command):
    # each domain is an argument before the value, the method's last parameter
    owners = [t for t, commands in NODE_COMMAND_SECTIONS.items() if command in commands]
    assert owners

    for node_type in owners:
        parameters = inspect.signature(
            getattr(NODE_CLASS[node_type], command)
        ).parameters
        assert len(_WILDCARD_DOMAINS[command]) < len(parameters) - 1


# input:    | any command whose enum argument takes a wildcard, e.g.
#           | set_power_transfer(*, *, 1.0)
# expected: -> each such argument has a written-out expansion in STAR_EXPANSION
#              below, so a new domain cannot go untested
def test_every_wildcard_domain_has_an_expansion_case():
    domains = {
        (command, position)
        for command, positions in _WILDCARD_DOMAINS.items()
        for position in range(len(positions))
    }
    assert domains == set(STAR_EXPANSION)


# input:    | e.g. set_slip_fraction(*, 0.5)
# expected: -> called once per fuel type, from (AMMONIA, 0.5) and
#              (ELECTRICITY, 0.5) through to (OIL, 0.5)
@pytest.mark.parametrize(
    ("command", "position"),
    list(STAR_EXPANSION),
    ids=[f"{command}[{position}]" for command, position in STAR_EXPANSION],
)
def test_a_bare_star_expands_to_the_domain(command, position):
    arity = len(inspect.signature(getattr(_Recorder, command)).parameters) - 1
    inputs = ["PROPULSION"] * (arity - 1) + [0.5]
    inputs[position] = "*"

    calls = _calls(command, inputs)

    assert [call[position] for call in calls] == STAR_EXPANSION[(command, position)]
    assert all(call[-1] == 0.5 for call in calls)


# input:    | e.g. set_slip_fraction(M*, 0.03)
# expected: -> (METHANE, 0.03), (METHANOL, 0.03)
#              and set_include_vessel(*, TRUE) -> ("*", TRUE), passed on unexpanded
@pytest.mark.parametrize(
    ("command", "inputs", "expected"),
    [
        (
            "set_slip_fraction",
            ["M*", 0.03],
            [("METHANE", 0.03), ("METHANOL", 0.03)],
        ),
        ("set_slip_fraction", ["?IL", 0.03], [("OIL", 0.03)]),
        ("set_slip_fraction", ["OIL", 0.03], [("OIL", 0.03)]),
        (
            # a wildcard past the domain is a node name, matched downstream
            "set_consumption_ttw",
            ["E*", "co2_*", 0.5],
            [("ELECTRICITY", "co2_*", 0.5), ("ETHANOL", "co2_*", 0.5)],
        ),
        (
            "set_power_transfer",
            ["*", "H*", 1.0],
            [
                ("PROPULSION", "HEAT", 1.0),
                ("ELECTRICAL", "HEAT", 1.0),
                ("HEAT", "HEAT", 1.0),
            ],
        ),
        ("set_include_vessel", ["*", "TRUE"], [("*", "TRUE")]),
    ],
    ids=[
        "prefix",
        "single_character",
        "no_wildcard",
        "beyond_the_domain",
        "two_domains_combine",
        "no_domain",
    ],
)
def test_a_wildcard_argument_expands_to_every_match(command, inputs, expected):
    assert _calls(command, inputs) == expected


# input:    | set_slip_fraction(X*, 0.03)
# expected: -> ValueError "wildcard 'X*' did not match any of AMMONIA, ELECTRICITY,
#              ETHANOL, HYDROGEN, LPG, METHANE, METHANOL, OIL"
def test_a_wildcard_matching_nothing_names_the_domain():
    message = (
        "wildcard 'X*' did not match any of AMMONIA, ELECTRICITY, ETHANOL, HYDROGEN, "
        "LPG, METHANE, METHANOL, OIL"
    )

    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        _calls("set_slip_fraction", ["X*", 0.03])
