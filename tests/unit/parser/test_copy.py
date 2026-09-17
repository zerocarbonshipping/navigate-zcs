# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Copy duplicates one node and shares the nodes it references.

Each copy is a new object carrying its own name, and what it points at stays
the single registry object.
"""

from __future__ import annotations

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.core.node_type import EMISSION, FUEL
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
ATTRIBUTE_HOST = SHARED + 'Emission "src" { GlobalWarmingPotential = Variable("w") }\n'
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


@pytest.mark.parametrize(
    ("define", "node_type", "group", "read"),
    [
        (
            ATTRIBUTE_HOST,
            EMISSION,
            "emissions",
            lambda node: node.global_warming_potential,
        ),
        (CONTAINER_HOST, FUEL, "fuels", lambda node: node.ttw["co2"]),
    ],
    ids=["attribute", "container"],
)
def test_the_copy_shares_a_resolved_reference(tmp_path, define, node_type, group, read):
    parser = _read_deck(tmp_path, define)
    shared = parser.nodes.variables["w"]
    # the reference walk has run, so the source holds the node itself; that is
    # the state the copy has to share
    assert read(getattr(parser.nodes, group)["src"]) is shared

    parser._current_section = SimulationSectionID.DEFINE
    parser._process_copy_node(CopyStatement(node_type, "src", "dst"))

    assert read(getattr(parser.nodes, group)["dst"]) is shared
