# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Copy duplicates one node and shares the nodes it references.

Each copy is a new object carrying its own name, and what it points at stays
the single registry object. A copy declared under a name that earlier
references named keeps what those references imposed on it. The commands
queued on the source run on the copy too, each on its own inputs.
"""

from __future__ import annotations

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.core.expression import Expression
from navigate.core.node_type import EMISSION
from navigate.core.nodes.emission import Emission
from navigate.parser._lark_parser import CopyStatement
from navigate.parser.parser import Parser

SHARED = 'Variable "w" { Value = 0.5 }\n'
# an Emission is a top-level node, so the Variable it references survives the
# unreachable-node prune (see the conftest module docstring)
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
CO2 = 'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'


def _fuel(name, ttw, emission="co2"):
    # the TTW factor is set by a command, so it sits in the parser's queue
    # until the commands run, after every declaration is read
    return f"""
Fuel "{name}" {{
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
    set_ttw("{emission}", {ttw})
}}
"""


def _fuel_library(tmp_path, files):
    """Write a default library holding the given Fuel files and return its root."""
    data_dir = tmp_path / "data"
    # mirror the shipped library: both branches carry a directory per node type
    for branch in ("user", "installation"):
        (data_dir / "defaults" / branch / "Fuel").mkdir(parents=True)
    for stem, content in files.items():
        (data_dir / "defaults" / "installation" / "Fuel" / f"{stem}.inc").write_text(
            content
        )
    return data_dir


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
def test_each_copy_is_a_new_node_and_the_source_keeps_its_name(
    read_deck, define, names
):
    parser = read_deck(define)
    nodes = [parser.nodes.emissions[name] for name in names]

    assert len({id(node) for node in nodes}) == len(names)
    assert "".join(node.name for node in nodes) == names


def test_the_copy_shares_a_reference_declared_after_the_copy(read_deck):
    define = ATTRIBUTE_SRC + 'Copy Emission "src" "dst"\n' + SHARED

    parser = read_deck(define)
    shared = parser.nodes.variables["w"]

    assert parser.nodes.emissions["src"].global_warming_potential is shared
    assert parser.nodes.emissions["dst"].global_warming_potential is shared


def test_the_copy_target_keeps_the_bounds_imposed_before_its_declaration(read_deck):
    # GlobalWarmingPotential allows no negative value, so the bound the reference
    # imposed on "v" clips the -2.0 the copy brings along
    define = (
        'Emission "e" { GlobalWarmingPotential = Variable("v") }\n'
        'Variable "base" { Value = -2.0 }\n'
        'Copy Variable "base" "v"\n'
    )

    parser = read_deck(define)

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
    read_deck, define, group, read
):
    parser = read_deck(define)
    shared = parser.nodes.variables["w"]

    assert read(getattr(parser.nodes, group)["src"]) is shared
    assert read(getattr(parser.nodes, group)["dst"]) is shared


class TestQueuedCommands:
    def test_a_command_queued_on_the_source_runs_on_the_source_and_the_copy(
        self, read_deck
    ):
        define = CO2 + _fuel("src", 2.75) + 'Copy Fuel "src" "dst"\n'

        parser = read_deck(define)

        assert parser.nodes.fuels["src"].ttw["co2"].get() == 2.75
        assert parser.nodes.fuels["dst"].ttw["co2"].get() == 2.75

    def test_an_expression_input_is_copied_and_bound_to_each_node(self, read_deck):
        # a setter stores the expression it is given, and the reference walk
        # binds it in place to the node holding it, so a shared one would stay
        # bound to whichever node the walk reached first
        define = (
            SHARED
            + CO2
            + _fuel("src", '<2 * Variable("w")>')
            + 'Copy Fuel "src" "dst"\n'
        )

        parser = read_deck(define)
        source = parser.nodes.fuels["src"]
        copied = parser.nodes.fuels["dst"]
        source_ttw = source.ttw["co2"]
        copied_ttw = copied.ttw["co2"]

        assert isinstance(source_ttw, Expression)
        assert isinstance(copied_ttw, Expression)
        assert source_ttw is not copied_ttw
        assert source_ttw._node is source
        assert copied_ttw._node is copied
        assert copied_ttw.get() == 1.0

    def test_the_copy_queue_replaces_the_queue_of_the_node_it_takes_over(
        self, read_deck, tmp_path
    ):
        # the pulled file declares the target's name too, so the copy moves into
        # that registered node, and the command the file queued on it is
        # dropped with the rest of the file's declaration
        library = {"src": _fuel("src", 2.75) + _fuel("dst", 9.0, emission="ch4")}
        define = (
            CO2
            + 'Emission "ch4" { GlobalWarmingPotential = 1.0 }\n'
            + 'Copy Fuel "src" "dst"\n'
        )

        parser = read_deck(define, data_dir=_fuel_library(tmp_path, library))
        copied = parser.nodes.fuels["dst"]

        assert copied.ttw["co2"].get() == 2.75
        assert copied.ttw["ch4"].get() == 0.0

    def test_a_source_pulled_from_the_library_leaves_no_queued_commands(
        self, read_deck, tmp_path
    ):
        # the source leaves the registry after the copy, so the drain, which
        # walks the registry, would never reach a queue left under it
        library = {"src": _fuel("src", 2.75)}
        define = CO2 + 'Copy Fuel "src" "dst"\n'

        parser = read_deck(define, data_dir=_fuel_library(tmp_path, library))

        assert "src" not in parser.nodes.fuels
        assert parser.nodes.fuels["dst"].ttw["co2"].get() == 2.75
        assert parser._command_queue == {}

    def test_a_source_pulled_from_the_library_onto_its_own_name_keeps_its_queue(
        self, read_deck, tmp_path
    ):
        # the pull registers "x" under its own name, so the transplant below
        # returns that same node: the copy's queue must survive the pop that
        # drops the source's entry once the pull is done
        library = {"x": _fuel("x", 2.75)}
        define = CO2 + 'Copy Fuel "x" "x"\n'

        parser = read_deck(define, data_dir=_fuel_library(tmp_path, library))

        assert parser.nodes.fuels["x"].ttw["co2"].get() == 2.75
