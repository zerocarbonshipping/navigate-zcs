# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Which node a `Type("name")` reference binds to, and when it cannot bind.

A reference to a declared node binds to it; a reference to an undeclared one
waits for a later declaration and otherwise pulls the node from the default
library, the user branch first. Every reference that can bind to nothing is a
located deck error.
"""

from __future__ import annotations

import logging
import re

import pytest

from helpers.parser_decks import emission_holding, line_of, variable, write_library
from navigate.exceptions import DeckFormatError, DeckKeywordError
from navigate.parser.parser import Parser

HOST = emission_holding('Variable("v")')
DEFAULT = variable(Value=3.0)
# a library node whose multiplier makes an unintended pull visible as 30.0
DECOY = variable(Value=3.0, Multiplier=10.0)
# a library file named for v that declares another node
WRONG_NAME = variable("w", Value=1.0)
OVERLAY = 'Import Variable "v"\n' + variable(Multiplier=2.0)
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
    """Read a deck against a synthesised two-branch Variable library."""

    def read(define, *, installation=None, user=None, events=None):
        data_dir = write_library(
            tmp_path / "data", "Variable", installation=installation, user=user
        )
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
        parser = read_library_deck(define, installation={"v": DECOY})
        node = parser.nodes.variables["v"]

        assert parser.nodes.emissions["e"].global_warming_potential is node
        assert node.get() == expected

    # input:    | Emission "e" { GlobalWarmingPotential = <2 * Variable("v")> }
    #           | no v in the deck; installation/Variable/v.inc has Value = 3.0
    # expected: -> v is pulled from the library and reads 3.0
    @pytest.mark.parametrize(
        "define",
        [HOST, 'Emission "e" { GlobalWarmingPotential = <2 * Variable("v")> }\n'],
        ids=["reference", "expression"],
    )
    def test_an_undeclared_name_is_pulled_from_the_library(
        self, read_library_deck, define
    ):
        parser = read_library_deck(define, installation={"v": DEFAULT})

        assert parser.nodes.variables["v"].get() == 3.0

    # input:    | Fuel "oil" { ... set_ttw("co2", Variable("v")) }
    #           | with no v in the deck
    # expected: -> v is pulled from installation/Variable/v.inc and reads 3.0
    def test_a_command_argument_pulls_its_default(self, read_library_deck):
        parser = read_library_deck(COMMAND_HOST, installation={"v": DEFAULT})

        assert parser.nodes.variables["v"].get() == 3.0

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | user/Variable/v.inc has Value = 5.0
    #           | installation/Variable/v.inc has Value = 3.0
    # expected: -> v reads 5.0, the user file wins
    def test_the_user_branch_shadows_the_installation_branch(self, read_library_deck):
        parser = read_library_deck(
            HOST, user={"v": variable(Value=5.0)}, installation={"v": DEFAULT}
        )

        assert parser.nodes.variables["v"].get() == 5.0

    # input:    | user/Variable/v.inc:
    #           |   Import Variable "v"
    #           |   Variable "v" { Multiplier = 2.0 }
    #           | installation/Variable/v.inc has Value = 3.0
    # expected: -> v reads 6.0, that is 2.0 times 3.0
    def test_a_user_file_importing_its_own_node_overlays_the_installation_one(
        self, read_library_deck
    ):
        # the Import inside the user file reads the installation v: 2.0 * 3.0
        parser = read_library_deck(
            HOST, user={"v": OVERLAY}, installation={"v": DEFAULT}
        )

        assert parser.nodes.variables["v"].get() == 6.0

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
    # expected: -> ghost is pruned with its command, and no error is raised for v
    def test_a_command_argument_on_a_pruned_node_needs_no_node(
        self, read_library_deck, caplog
    ):
        # no Vessel mounts the converter, so the prune removes it with its
        # queued command before any walk reaches the argument
        define = 'Converter "ghost" {\n    set_slip_fraction(OIL, Variable("v"))\n}\n'

        with caplog.at_level(logging.WARNING):
            parser = read_library_deck(define)

        assert "ghost" not in parser.nodes.converters


class TestUnresolvable:
    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | no v in the deck or the library
    # expected: -> DeckKeywordError "...define.inc', line 6: Variable("v") is
    #              referenced but not found in either the deck or the default
    #              location of Variable."
    def test_a_missing_default_names_the_type_name_and_location(
        self, read_library_deck
    ):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"include file '.*define\.inc', line 6: "
                r'Variable\("v"\) is referenced but not found in either the deck '
                r"or the default location of Variable\.$"
            ),
        ):
            read_library_deck(HOST)

    # input:    | Emission "e" { GlobalWarmingPotential = Foo("x") }
    # expected: -> DeckKeywordError "...line 6: 'Foo' is not a recognized node
    #              type."
    def test_an_unknown_reference_type_is_rejected(self, read_library_deck):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"include file '.*define\.inc', line 6: "
                r"'Foo' is not a recognized node type\.$"
            ),
        ):
            read_library_deck(emission_holding('Foo("x")'))

    # input:    | Emission "e" { GlobalWarmingPotential = <2 * Variable("v*")> }
    # expected: -> DeckFormatError "Error in node reference: Must not contain
    #              wildcards."
    def test_a_wildcard_inside_an_expression_is_rejected(self, read_library_deck):
        with pytest.raises(
            DeckFormatError,
            match=r"Error in node reference: Must not contain wildcards\.$",
        ):
            read_library_deck(emission_holding('<2 * Variable("v*")>'))

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | installation/Variable/v.inc holds   Emission "v" { }   (wrong type)
    # expected: -> DeckKeywordError "...A file with name 'v' was found, but not
    #              containing a node with type 'Variable' and similar name."
    @pytest.mark.parametrize(
        ("define", "library"),
        [
            (HOST, {"installation": {"v": 'Emission "v" { }\n'}}),
            # a user file found by name ends the search, so the installation
            # file is no fallback
            (HOST, {"user": {"v": WRONG_NAME}, "installation": {"v": DEFAULT}}),
            ('Import Variable "v"\n', {"user": {"v": WRONG_NAME}}),
            ('Copy Variable "v" "dst"\n', {"user": {"v": WRONG_NAME}}),
        ],
        ids=["wrong_type", "user_over_installation", "import", "copy"],
    )
    def test_a_file_without_the_requested_node_is_rejected(
        self, read_library_deck, define, library
    ):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"include file '.*define\.inc', line \d+: A file with name 'v' was "
                r"found, but not containing a node with type 'Variable' and "
                r"similar name\.$"
            ),
        ):
            read_library_deck(define, **library)

    # input:    | installation/Variable/v.inc:
    #           |   Import Variable "v"
    #           |   Variable "v" { Multiplier = 2.0 }
    # expected: -> DeckKeywordError "Variable("v") is pulled from the default
    #              library while its own installation default ... is being read. ..."
    def test_an_installation_file_pulling_its_own_node_is_rejected(
        self, read_library_deck
    ):
        # nothing lies beyond the installation branch, so the pull would
        # re-read the same file forever
        with pytest.raises(
            DeckKeywordError,
            match=(
                r'Variable\("v"\) is pulled from the default library while its own '
                r"installation default in '.*Variable' is being read\. A default "
                r"file cannot import or copy its own node\.$"
            ),
        ):
            read_library_deck(HOST, installation={"v": OVERLAY})

    # input:    | Emission "e" { GlobalWarmingPotential = Variable("v") }
    #           | read with no assumptions directory at all
    # expected: -> DeckKeywordError "Error in deck file, line 1: Default
    #              Variable("v") is requested but no assumptions directory ..."
    def test_a_reference_without_an_assumptions_directory_is_rejected(self, write_deck):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r'^Error in deck file, line 1: Default Variable\("v"\) is requested '
                r"but no assumptions directory"
            ),
        ):
            Parser().read_deck(write_deck(HOST))


def _unresolved(reference, holder, first_referenced):
    """Match the never-resolved error's entry for a reference with one holder."""
    return (
        rf"\n\t- {re.escape(reference)}\n\t  held by {re.escape(holder)}\n"
        rf"\t  first referenced at [^\n]*{re.escape(first_referenced)}\n"
    )


class TestNeverResolved:
    """
    A node held where the parser resolves no reference is reported, not run.

    The reference walk never sees it, so it is neither declared nor pulled;
    the error lists each such node with every holder and its first reference.
    """

    # input:    | Plot "p" { add_plot(Variable("ghost")) }   with no ghost anywhere
    # expected: -> DeckKeywordError "Node reference(s) left unresolved, ...
    #              Variable("ghost") held by Plot("p") attribute 'selected_plots' first
    #              referenced at ...define.inc', line N"
    @pytest.mark.parametrize(
        ("define", "reference", "holder"),
        [
            # add_plot keeps its argument in a set
            (PLOT_GHOST, 'Variable("ghost")', "Plot(\"p\") attribute 'selected_plots'"),
            # add_fleet_property keys its report dictionary by the argument
            (
                'Report "r" {\n    add_fleet_property(Fleet("ghost"), CargoMiles)\n}\n',
                'Fleet("ghost")',
                "Report(\"r\") attribute 'fleet_reports'",
            ),
        ],
        ids=["plot_set", "report_dict_key"],
    )
    def test_a_node_where_a_name_is_expected_is_rejected(
        self, tmp_path, read_library_deck, define, reference, holder
    ):
        with pytest.raises(DeckKeywordError) as error:
            read_library_deck(define)

        line = line_of(tmp_path / "define.inc", reference)
        entry = _unresolved(reference, holder, f"define.inc', line {line}")
        assert str(error.value).startswith(
            "Node reference(s) left unresolved, the node neither declared in the "
            "deck nor looked up in the default library:"
        )
        assert re.search(entry, str(error.value))

    # input:    | Fuel "oil" { ... set_ttw("co2", Variable("v")) }
    #           | installation/Variable/v.inc:
    #           |   Variable "v" { Value = 3.0 }
    #           |   Fuel "oil" { set_ttw("co2", Variable("w")) }
    # expected: -> DeckKeywordError naming Variable("w") held by command
    #              'set_ttw' on Fuel("oil") at v.inc', line N
    def test_a_command_queued_after_define_resolved_is_rejected(
        self, tmp_path, read_library_deck
    ):
        # v is a command argument, so the walk after the commands pulls it, and
        # nothing walks the command its file queues before EVENTS
        late_file = DEFAULT + 'Fuel "oil" { set_ttw("co2", Variable("w")) }\n'

        with pytest.raises(DeckKeywordError) as error:
            read_library_deck(COMMAND_HOST, installation={"v": late_file})

        library_file = tmp_path / "data/defaults/installation/Variable/v.inc"
        at = f"v.inc', line {line_of(library_file, 'Variable("w")')}"
        message = str(error.value)
        assert (
            '\n\t- Variable("w")\n\t  held by command \'set_ttw\' on Fuel("oil") at '
            in message
        )
        assert message.count(at) == 2
