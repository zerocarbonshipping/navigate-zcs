# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Which node a `Type("name")` reference binds to, and when it cannot bind.

A reference to a declared node binds to it, wherever the declaration stands in
the deck; a reference to an undeclared one pulls the node from the default
library. Every reference that can bind to nothing is a
located deck error, wherever the reference is written.
"""

from __future__ import annotations

import logging

import pytest

from helpers.parser_decks import emission_holding, line_of, variable, write_library
from navigate.exceptions import DeckError
from navigate.parser.parser import Parser

HOST = emission_holding('Variable("v")')
DEFAULT = variable(Value=3.0)
# a library node whose multiplier makes an unintended pull visible as 30.0
DECOY = variable(Value=3.0, Multiplier=10.0)
# a library file named for v that declares another node
WRONG_NAME = variable("w", Value=1.0)
COMMAND_HOST = """
Emission "co2" { }

Fuel "oil" {
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
    set_ttw("co2", Variable("v"))
}
"""
PLOT_GHOST = 'Plot "p" {\n    add_plot(Variable("ghost"))\n}\n'


@pytest.fixture
def read_library_deck(tmp_path, read_deck):
    """Read a deck against a synthesised Variable library."""

    def read(define, *, library=None, events=None):
        data_dir = write_library(tmp_path / "data", "Variable", library)
        return read_deck(define, events=events, data_dir=data_dir)

    return read


class TestBinding:
    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | Variable "v" { Value = 1.0 }
    #           | library v.inc: Value = 3.0 and Multiplier = 10.0
    # expected: -> e holds the deck's v, which reads 1.0 and not 30.0
    @pytest.mark.parametrize(
        ("define", "expected"),
        [
            (HOST + variable(Value=1.0), 1.0),
            (variable(Value=1.0) + HOST, 1.0),
            (HOST + variable("src", Value=4.0) + 'Copy Variable "src" "v"\n', 4.0),
        ],
        ids=["declared_after", "declared_before", "copy_target"],
    )
    def test_a_deck_declaration_shadows_the_library(
        self, read_library_deck, define, expected
    ):
        parser = read_library_deck(define, library={"v": DECOY})
        node = parser.nodes.variables["v"]

        assert parser.nodes.emissions["e"].global_warming_potential is node
        assert node.get() == expected

    # input:    | Emission "e" { GlobalWarmingPotential = <2 * Variable("v")> }
    #           | no v in the deck; defaults/Variable/v.inc has Value = 3.0
    # expected: -> v is pulled from the library and reads 3.0
    @pytest.mark.parametrize(
        "define",
        [HOST, 'Emission "e" { GlobalWarmingPotential = <2 * Variable("v")> }\n'],
        ids=["reference", "expression"],
    )
    def test_an_undeclared_name_is_pulled_from_the_library(
        self, read_library_deck, define
    ):
        parser = read_library_deck(define, library={"v": DEFAULT})

        assert parser.nodes.variables["v"].get() == 3.0

    # input:    | Fuel "oil" { ... set_ttw("co2", Variable("v")) }
    #           | with no v in the deck
    # expected: -> v is pulled from defaults/Variable/v.inc and reads 3.0
    def test_a_command_argument_pulls_its_default(self, read_library_deck):
        parser = read_library_deck(COMMAND_HOST, library={"v": DEFAULT})

        assert parser.nodes.variables["v"].get() == 3.0

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | Emission "e" { GlobalWarmingPotential = 1.0 }   with an empty library
    # expected: -> no error, no Variable "v" is created, and e reads 1.0
    def test_a_reference_a_later_assignment_overwrote_needs_no_node(
        self, read_library_deck
    ):
        define = HOST + 'Emission "e" { GlobalWarmingPotential = 1.0 }\n'

        parser = read_library_deck(define)

        assert "v" not in parser.nodes.variables
        assert parser.nodes.emissions["e"].global_warming_potential.get() == 1.0

    # input:    | Converter "ghost" { set_slip_fraction(OIL, Variable("v")) }
    #           | no vessel mounts ghost; empty library
    # expected: -> ghost is left out with its command, and no error is raised for v
    def test_a_command_argument_on_an_unused_node_needs_no_node(
        self, read_library_deck, caplog
    ):
        # no Vessel mounts the converter, so nothing walks its references
        define = 'Converter "ghost" {\n    set_slip_fraction(OIL, Variable("v"))\n}\n'

        with caplog.at_level(logging.WARNING):
            parser = read_library_deck(define)

        assert "ghost" not in parser.nodes.converters


class TestUnresolvable:
    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | no v in the deck or the library
    # expected: -> DeckError "...define.inc', line 6: Variable("v") is
    #              referenced but not found in either the deck or the default
    #              location of Variable."
    def test_a_missing_default_names_the_type_name_and_location(
        self, read_library_deck
    ):
        with pytest.raises(
            DeckError,
            match=(
                r"include file '.*define\.inc', line 6: "
                r'Variable\("v"\) is referenced but not found in either the deck '
                r"or the default location of Variable\.$"
            ),
        ):
            read_library_deck(HOST)

    # input:    | Emission "e" { GlobalWarmingPotential = Foo("x") }
    # expected: -> DeckError "...line 6: 'Foo' is not a recognized node type."
    def test_an_unknown_reference_type_is_rejected(self, read_library_deck):
        with pytest.raises(
            DeckError,
            match=(
                r"include file '.*define\.inc', line 6: "
                r"'Foo' is not a recognized node type\.$"
            ),
        ):
            read_library_deck(emission_holding('Foo("x")'))

    # input:    | Emission "e" { GlobalWarmingPotential = <2 * Variable("v*")> }
    # expected: -> DeckError "...line 6: Expression references Variable("v*"): a
    #              node reference in an expression must not contain wildcards."
    def test_a_wildcard_inside_an_expression_is_rejected(self, read_library_deck):
        with pytest.raises(
            DeckError,
            match=(
                r"define\.inc', line 6: Expression references Variable\(\"v\*\"\): "
                r"a node reference in an expression must not contain wildcards\.$"
            ),
        ):
            read_library_deck(emission_holding('<2 * Variable("v*")>'))

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | defaults/Variable/v.inc holds   Emission "v" { }   (wrong type)
    # expected: -> DeckError "...A file with name 'v' was found, but not
    #              containing a node with type 'Variable' and similar name."
    @pytest.mark.parametrize(
        ("define", "library"),
        [
            (HOST, {"v": 'Emission "v" { }\n'}),
            ('Import Variable "v"\n', {"v": WRONG_NAME}),
            ('Copy Variable "v" "dst"\n', {"v": WRONG_NAME}),
        ],
        ids=["wrong_type", "import", "copy"],
    )
    def test_a_file_without_the_requested_node_is_rejected(
        self, read_library_deck, define, library
    ):
        with pytest.raises(
            DeckError,
            match=(
                r"include file '.*define\.inc', line \d+: A file with name 'v' was "
                r"found, but not containing a node with type 'Variable' and "
                r"similar name\.$"
            ),
        ):
            read_library_deck(define, library=library)

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | self:  v.inc imports v
    #           | cycle: v.inc imports w, w.inc imports v
    # expected: -> DeckError "...<file>.inc', line 1: Variable("v") is pulled
    #              from the default library while its own default file is being
    #              read. ...", at the Import that re-enters v
    @pytest.mark.parametrize(
        ("library", "file"),
        [
            ({"v": 'Import Variable "v"\n' + DEFAULT}, "v"),
            (
                {
                    "v": 'Import Variable "w"\n' + DEFAULT,
                    "w": 'Import Variable "v"\n' + variable("w", Value=1.0),
                },
                "w",
            ),
        ],
        ids=["self", "cycle"],
    )
    def test_default_files_pulling_each_other_in_a_cycle_are_rejected(
        self, read_library_deck, library, file
    ):
        # re-reading a file that is being read would read it forever
        with pytest.raises(
            DeckError,
            match=(
                rf"{file}\.inc', line 1: "
                r'Variable\("v"\) is pulled from the default library while its own '
                r"default file is being read\. Default files cannot import or copy "
                r"each other in a cycle\.$"
            ),
        ):
            read_library_deck(HOST, library=library)

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | read with no assumptions directory at all
    # expected: -> DeckError "Error in deck file, line 1, include file '...', line
    #              6: Default Variable("v") is requested but no assumptions
    #              directory ..."
    def test_a_reference_without_an_assumptions_directory_is_rejected(self, write_deck):
        with pytest.raises(
            DeckError,
            match=(
                r"^Error in deck file, line 1, include file '.*define\.inc', line 6: "
                r'Default Variable\("v"\) is requested but no assumptions directory'
            ),
        ):
            Parser().read_deck(write_deck(HOST))


class TestReferenceSites:
    """
    A reference is resolved wherever it is written, before any setter runs.

    A command argument the setter would keep as a set member or a dictionary
    key, or a command a library file adds to a deck node, is walked like any
    other reference, so an undeclared name is the missing-default error.
    """

    # input:    | Plot "p" { add_plot(Variable("ghost")) }   with no ghost anywhere
    # expected: -> DeckError "...define.inc', line N: Variable("ghost") is
    #              referenced but not found in either the deck or the default
    #              location of Variable."
    @pytest.mark.parametrize(
        ("define", "reference", "node_type"),
        [
            # add_plot keeps its argument in a set
            (PLOT_GHOST, 'Variable("ghost")', "Variable"),
            # add_fleet_property keys its report dictionary by the argument
            (
                'Report "r" {\n    add_fleet_property(Fleet("ghost"), CargoMiles)\n}\n',
                'Fleet("ghost")',
                "Fleet",
            ),
        ],
        ids=["plot_set", "report_dict_key"],
    )
    def test_a_node_where_a_name_is_expected_is_resolved(
        self, tmp_path, read_library_deck, define, reference, node_type
    ):
        with pytest.raises(DeckError) as error:
            read_library_deck(define)

        line = line_of(tmp_path / "define.inc", reference)
        assert str(error.value).endswith(
            f"define.inc', line {line}: {reference} is referenced but not found in "
            f"either the deck or the default location of {node_type}."
        )

    # input:    | Fuel "oil" { ... set_ttw("co2", Variable("v")) }
    #           | defaults/Variable/v.inc:
    #           |   Variable "v" { Value = 3.0 }
    #           |   Fuel "oil" { set_ttw("co2", Variable("w")) }
    # expected: -> DeckError "...v.inc', line N: Variable("w") is referenced but
    #              not found ..." for the command the library file adds
    def test_a_command_a_library_file_adds_to_a_deck_node_is_resolved(
        self, tmp_path, read_library_deck
    ):
        late_file = DEFAULT + 'Fuel "oil" { set_ttw("co2", Variable("w")) }\n'

        with pytest.raises(DeckError) as error:
            read_library_deck(COMMAND_HOST, library={"v": late_file})

        library_file = tmp_path / "data/defaults/Variable/v.inc"
        assert str(error.value).endswith(
            f"v.inc', line {line_of(library_file, 'Variable("w")')}: "
            'Variable("w") is referenced but not found in either the deck or the '
            "default location of Variable."
        )
