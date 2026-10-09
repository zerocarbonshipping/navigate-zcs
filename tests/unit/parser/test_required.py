# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The parser raises for a required attribute no DEFINE assignment reached.

`BASE` declares one node of every type with required attributes, each
reachable from a root so the unreachable-node prune keeps it, and each
assigned every attribute `NODE_REQUIRED_ATTRIBUTES` requires of it. Every
required attribute is then dropped from it in turn, and the deck read must
name exactly that one: the check reports the first unassigned attribute it
meets, so a case also fails if `BASE` misses another one.

The check reads which setters the parser ran, so an assignment counts however
it reached the node: directly, through a wildcard, or carried by a Copy.
"""

from __future__ import annotations

import re

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.exceptions import DeckFormatError
from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    GENERAL_NODE_REQUIRED_ATTRIBUTES,
    NODE_ATTRIBUTE_SECTIONS,
    NODE_REQUIRED_ATTRIBUTES,
)

TABLE_1D = "Table = [\n        0 1\n        1 1\n    ]"

# (node type, name, body items); every non-root node hangs off a root:
# Fleet -> Vessel -> PowerSystem/Converter, Route/Port, Tank, Surface;
# Producer -> Plant -> Fuel, Process, Region -> Timetable, Source;
# Emission -> Curve; Levy -> Forecast
BASE = [
    ("Fuel", "f", ["FuelType = OIL", "LowerHeatingValue = 40", "MassDensity = 900"]),
    (
        "Converter",
        "c",
        ["PowerCapacity = 10", "Efficiency = 0.5", "MainFuelTypes = OIL"],
    ),
    (
        "PowerSystem",
        "ps",
        [
            'Propulsion = Converter("c")',
            'Electrical = Converter("c")',
            'Heat = Converter("c")',
        ],
    ),
    ("Port", "a", []),
    ("Port", "b", []),
    ("Route", "r", ["RouteType = ROUND_TRIP", 'Ports = [Port("a"), Port("b")]']),
    ("Tank", "t", ["FuelTypes = OIL", "Size = 100"]),
    ("Surface", "s", ["Table = [\n        0 1\n        0 1 2\n        1 3 4\n    ]"]),
    (
        "Vessel",
        "v",
        [
            'PowerSystem = PowerSystem("ps")',
            'Route = Route("r")',
            "NominalCapacity = 1000",
            'Tanks = [Tank("t")]',
            'PropulsionLoad = Surface("s")',
        ],
    ),
    (
        "Fleet",
        "fl",
        [
            'Vessels = [Vessel("v")]',
            "InitialVessels = 10",
            "InterFuelSensitivity = 1",
            "IntraFuelSensitivity = 1",
        ],
    ),
    ("Curve", "cu", [TABLE_1D]),
    ("Emission", "e", ['GlobalWarmingPotential = Curve("cu")']),
    ("Forecast", "fc", [TABLE_1D]),
    ("Levy", "l", ["Scheme = PENALTY", 'Level = Forecast("fc")']),
    ("Regulation", "rg", ["Scheme = INDIVIDUAL", "Measure = ABSOLUTE"]),
    ("Source", "src", ["Dependency = STANDALONE"]),
    ("Process", "p", []),
    (
        "Timetable",
        "tt",
        [
            "Table = [\n        0 1\n        "
            '"01-01-2026" 1 2\n        "01-01-2030" 1 2\n    ]'
        ],
    ),
    ("Region", "rgn", ['set_process_capex("p", Timetable("tt"))']),
    (
        "Plant",
        "pl",
        [
            'Fuel = Fuel("f")',
            'Process = Process("p")',
            'Region = Region("rgn")',
            'Source = Source("src")',
            "Capacity = 100",
        ],
    ),
    (
        "Producer",
        "pr",
        [
            'Plants = [Plant("pl")]',
            "FuelDemandSensitivity = 1",
            "FuelCostSensitivity = 1",
            "MaximumDevelopment = 1",
        ],
    ),
]

NAMES = {node_type: name for node_type, name, _ in BASE}

REQUIRED = [
    pytest.param(node_type, attribute, id=f"{node_type}.{attribute}")
    for node_type, attributes in NODE_REQUIRED_ATTRIBUTES.items()
    for attribute in attributes
]

FUEL = """
Fuel "{name}" {{
    FuelType = OIL
    LowerHeatingValue = 41.2
{mass_density}}}
"""
MASS_DENSITY = "    MassDensity = 0.9\n"


def _deck(without: tuple[str, str] | None = None) -> str:
    """Render BASE, leaving out one required attribute of one node type."""
    text = ""
    for node_type, name, body in BASE:
        items = [item for item in body if (node_type, item.split(" ", 1)[0]) != without]
        text += f'{node_type} "{name}" {{\n'
        text += "".join(f"    {item}\n" for item in items)
        text += "}\n"
    return text


def _fuel(name: str = "f", mass_density: str = MASS_DENSITY) -> str:
    return FUEL.format(name=name, mass_density=mass_density)


# input:    | Fuel "f" { MassDensity = 0.9 }   in DEFINE
# expected: -> every required attribute, e.g. Fuel.MassDensity, is allowed in DEFINE,
#              so a deck can always assign it
@pytest.mark.parametrize(
    ("required", "sections"),
    [
        (NODE_REQUIRED_ATTRIBUTES, NODE_ATTRIBUTE_SECTIONS),
        (GENERAL_NODE_REQUIRED_ATTRIBUTES, GENERAL_NODE_ATTRIBUTE_SECTIONS),
    ],
    ids=["node", "general_node"],
)
def test_every_required_attribute_is_assignable_in_define(required, sections):
    # a required attribute DEFINE could not assign would fail every deck
    for node_type, attributes in required.items():
        for attribute in attributes:
            assert SimulationSectionID.DEFINE in sections[node_type][attribute]


# input:    | e.g. Fuel "f" {
#           |          FuelType = OIL
#           |          LowerHeatingValue = 40
#           |      }                              (MassDensity left out)
# expected: -> ValueError "Fuel("f"): Attribute 'MassDensity' is unassigned."
@pytest.mark.parametrize(("node_type", "attribute"), REQUIRED)
def test_a_missing_required_attribute_is_named(read_deck, node_type, attribute):
    message = (
        f"{node_type}(\"{NAMES[node_type]}\"): Attribute '{attribute}' is unassigned."
    )

    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        read_deck(_deck(without=(node_type, attribute)))


# input:    | ModelDefinition {
#           | }                    (StartDate left out)
# expected: -> ValueError "ModelDefinition: Attribute 'StartDate' is unassigned."
@pytest.mark.parametrize(
    ("type_", "attribute"),
    [
        (type_, attribute)
        for type_, attributes in GENERAL_NODE_REQUIRED_ATTRIBUTES.items()
        for attribute in attributes
    ],
)
def test_a_missing_required_general_node_attribute_is_named(
    read_deck, type_, attribute
):
    message = f"{type_}: Attribute '{attribute}' is unassigned."

    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        read_deck(_fuel(), define_base=f"{type_} {{\n}}\n")


# input:    | a DEFINE section holding only a Fuel, no ModelDefinition block
# expected: -> DeckFormatError "Error in simulation: 'ModelDefinition' must be defined."
def test_a_deck_without_a_model_definition_is_rejected(read_deck):
    with pytest.raises(
        DeckFormatError,
        match=r"^Error in simulation: 'ModelDefinition' must be defined\.$",
    ):
        read_deck(_fuel(), define_base="")


# input:    | Fuel "f" { ... }
#           | Curve "unused" {
#           | }                    (no Table, and nothing references the Curve)
# expected: -> no error; the Curve is pruned before its missing Table is checked
def test_an_unreachable_node_is_pruned_before_the_check(read_deck):
    # the Curve misses its required Table, but no root reaches it
    parser = read_deck(_fuel() + 'Curve "unused" {\n}\n')

    assert parser.nodes.curves == {}


# input:    | Fuel "f" { FuelType = OIL  LowerHeatingValue = 41.2 }
#           | Fuel "*" {
#           |     MassDensity = 0.9
#           | }
# expected: -> no error; Fuel "f" has MassDensity 0.9
def test_a_wildcard_assignment_counts(read_deck):
    parser = read_deck(_fuel(mass_density="") + 'Fuel "*" {\n' + MASS_DENSITY + "}\n")

    assert parser.nodes.fuels["f"].mass_density.get() == 0.9


# input:    | Fuel "f" { FuelType = OIL  LowerHeatingValue = 41.2 }
#           | Fuel "f" {
#           |     MassDensity = 0.9
#           | }
# expected: -> no error; the second block re-opens "f" and sets MassDensity 0.9
def test_an_assignment_in_a_later_declaration_counts(read_deck):
    parser = read_deck(_fuel(mass_density="") + 'Fuel "f" {\n' + MASS_DENSITY + "}\n")

    assert parser.nodes.fuels["f"].mass_density.get() == 0.9


# input:    | Fuel "a" { FuelType = OIL  LowerHeatingValue = 41.2  MassDensity = 0.9 }
#           | Copy Fuel "a" "b"
# expected: -> no error; Fuel "b" has MassDensity 0.9, copied from "a"
def test_a_copy_carries_the_assignments_of_its_source(read_deck):
    parser = read_deck(_fuel(name="a") + 'Copy Fuel "a" "b"\n')

    assert parser.nodes.fuels["b"].mass_density.get() == 0.9
