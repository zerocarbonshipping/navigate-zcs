# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Copy duplicates one node and shares the nodes it references.

Each copy is a new object carrying its own name, and what it points at stays
the single registry object. A copy declared under a name that earlier
references named keeps what those references imposed on it.
"""

from __future__ import annotations

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.core.node_type import EMISSION
from navigate.core.nodes.emission import Emission
from navigate.parser._lark_parser import CopyStatement
from navigate.parser.parser import Parser

MODEL_DEFINITION = """
ModelDefinition {
    StartDate = "01-01-2026"
}
"""
SHARED = 'Variable "w" { Value = 0.5 }\n'
# an Emission is a top-level node, so the Variable it references survives the
# unreachable-node prune
ATTRIBUTE_SRC = 'Emission "src" { GlobalWarmingPotential = Variable("w") }\n'
ATTRIBUTE_HOST = SHARED + ATTRIBUTE_SRC
CONTAINER_HOST = (
    SHARED
    + """
Emission "co2" { GlobalWarmingPotential = 1.0 }
Fuel "src" {
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
    set_ttw("co2", Variable("w"))
}
"""
)


def _read_deck(tmp_path, define):
    (tmp_path / "define.inc").write_text(MODEL_DEFINITION + define)
    deck = tmp_path / "deck.nav"
    deck.write_text('DEFINE { Include "define.inc" }\nEVENTS { }\n')

    parser = Parser()
    # no assumptions tree: any unintended pull from the default library fails
    parser.read_deck(deck, data_dir=tmp_path / "data")
    return parser


@pytest.mark.parametrize(
    ("define", "names"),
    [
        (
            'Emission "a" { GlobalWarmingPotential = 1.0 }\nCopy Emission "a" "b"\n',
            "ab",
        ),
        (
            'Emission "a" { GlobalWarmingPotential = 1.0 }\n'
            'Copy Emission "a" "b"\nCopy Emission "b" "c"\n',
            "abc",
        ),
    ],
    ids=["single", "chain"],
)
def test_each_copy_is_a_new_node_and_the_source_keeps_its_name(tmp_path, define, names):
    parser = _read_deck(tmp_path, define)
    nodes = [parser.nodes.emissions[name] for name in names]

    assert len({id(node) for node in nodes}) == len(names)
    assert "".join(node.name for node in nodes) == names


def test_the_copy_shares_a_reference_declared_after_the_copy(tmp_path):
    define = ATTRIBUTE_SRC + 'Copy Emission "src" "dst"\n' + SHARED

    parser = _read_deck(tmp_path, define)
    shared = parser.nodes.variables["w"]

    assert parser.nodes.emissions["src"].global_warming_potential is shared
    assert parser.nodes.emissions["dst"].global_warming_potential is shared


def test_the_copy_target_keeps_the_bounds_imposed_before_its_declaration(tmp_path):
    # GlobalWarmingPotential allows no negative value, so the bound the reference
    # imposed on "v" clips the -2.0 the copy brings along
    define = (
        'Emission "e" { GlobalWarmingPotential = Variable("v") }\n'
        'Variable "base" { Value = -2.0 }\n'
        'Copy Variable "base" "v"\n'
    )

    parser = _read_deck(tmp_path, define)

    assert parser.nodes.variables["v"].get() == 0.0


def test_a_copy_target_without_a_calculator_adopts_its_placeholder():
    # a node without bounds to merge back is adopted all the same
    parser = Parser()
    parser._current_section = SimulationSectionID.DEFINE
    placeholder = parser._node(EMISSION, "dst", location="")
    source = Emission("src")
    source.set_global_warming_potential(2.0)
    parser.nodes.emissions["src"] = source

    parser._process_copy_node(CopyStatement(EMISSION, "src", "dst"))

    assert parser.nodes.emissions["dst"] is placeholder
    assert placeholder.global_warming_potential.get() == 2.0


@pytest.mark.parametrize(
    ("define", "group", "read"),
    [
        (
            ATTRIBUTE_HOST + 'Copy Emission "src" "dst"\n',
            "emissions",
            lambda node: node.global_warming_potential,
        ),
        (
            CONTAINER_HOST + 'Copy Fuel "src" "dst"\n',
            "fuels",
            lambda node: node.ttw["co2"],
        ),
    ],
    ids=["attribute", "container"],
)
def test_the_copy_shares_a_reference_declared_before_the_copy(
    tmp_path, define, group, read
):
    parser = _read_deck(tmp_path, define)
    shared = parser.nodes.variables["w"]

    assert read(getattr(parser.nodes, group)["src"]) is shared
    assert read(getattr(parser.nodes, group)["dst"]) is shared
