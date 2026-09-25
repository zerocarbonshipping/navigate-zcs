# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The parser raises for a required attribute no DEFINE assignment reached.

A Fuel requires FuelType, LowerHeatingValue and MassDensity, and ModelDefinition
requires StartDate. The check reads which setters the parser ran, so an
assignment counts however it reached the node: directly, through a wildcard,
or carried over by a Copy.
"""

from __future__ import annotations

import pytest

FUEL = """
Fuel "{name}" {{
    FuelType = OIL
    LowerHeatingValue = 41.2
{mass_density}}}
"""
MASS_DENSITY = "    MassDensity = 0.9\n"


def _fuel(name="f", mass_density=MASS_DENSITY):
    return FUEL.format(name=name, mass_density=mass_density)


def test_a_node_missing_a_required_attribute_raises(read_deck):
    with pytest.raises(
        ValueError, match=r"Fuel\(\"f\"\): Attribute 'MassDensity' is unassigned"
    ):
        read_deck(_fuel(mass_density=""))


def test_a_node_with_every_required_attribute_assigned_reads(read_deck):
    parser = read_deck(_fuel())

    assert parser.nodes.fuels["f"].mass_density.get() == 0.9


def test_a_wildcard_assignment_counts(read_deck):
    define = _fuel(mass_density="") + 'Fuel "*" {\n' + MASS_DENSITY + "}\n"

    parser = read_deck(define)

    assert parser.nodes.fuels["f"].mass_density.get() == 0.9


def test_a_copy_carries_the_assignments_of_its_source(read_deck):
    parser = read_deck(_fuel(name="a") + 'Copy Fuel "a" "b"\n')

    assert parser.nodes.fuels["b"].mass_density.get() == 0.9


def test_a_general_node_missing_a_required_attribute_raises(read_deck):
    with pytest.raises(
        ValueError, match="ModelDefinition: Attribute 'StartDate' is unassigned"
    ):
        read_deck(_fuel(), define_base="ModelDefinition {\n}\n")
