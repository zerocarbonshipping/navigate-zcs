# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The statements that bring nodes in from elsewhere: Copy, Import, Load.

Copy duplicates one node, sharing what it references and replaying its queued
commands on the copy. Import pulls named or globbed nodes from the default
library, and Load reads a module; Include is covered with the sections.
Each is DEFINE-only where it creates nodes, and each failure is a located deck
error.
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import emission_holding, variable, write_library
from navigate.core.expression import Expression
from navigate.core.node_type import MODEL_DEFINITION
from navigate.exceptions import DeckFormatError, DeckKeywordError
from navigate.parser.parser import Parser

SHARED = variable("w", Value=0.5)
CO2 = 'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'
DEFAULT = variable(Value=3.0)


def _fuel(name, ttw):
    # the TTW factor is set by a command, so it sits in the parser's queue
    # until the commands run, after every declaration is read
    return f"""
Fuel "{name}" {{
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
    set_ttw("co2", {ttw})
}}
"""


def _write_nav(tmp_path, define_directives, events_directives=""):
    """Write define.inc with a ModelDefinition and a deck.nav of raw directives."""
    (tmp_path / "define.inc").write_text(
        'ModelDefinition {\n    StartDate = "01-01-2026"\n}\n'
    )
    deck = tmp_path / "deck.nav"
    deck.write_text(
        f'DEFINE {{\n    Include "define.inc"\n{define_directives}}}\n'
        f"EVENTS {{\n{events_directives}}}\n"
    )
    return deck


class TestCopy:
    # input:    | Emission "a" { GlobalWarmingPotential = 1.0 }
    #           | Copy Emission "a" "b"
    #           | Copy Emission "b" "c"
    # expected: -> three separate Emission nodes named "a", "b" and "c"
    def test_each_copy_is_a_new_node_under_its_own_name(self, read_deck):
        define = CO2.replace('"co2"', '"a"') + (
            'Copy Emission "a" "b"\nCopy Emission "b" "c"\n'
        )

        parser = read_deck(define)
        nodes = [parser.nodes.emissions[name] for name in "abc"]

        assert len({id(node) for node in nodes}) == 3
        assert [node.name for node in nodes] == ["a", "b", "c"]

    # input:    | Emission "src" { GlobalWarmingPotential = Variable("w") }
    #           | Copy Emission "src" "dst"
    #           | (Variable "w" declared before or after the Copy)
    # expected: -> "src" and "dst" both hold the same Variable "w" object
    @pytest.mark.parametrize(
        "define",
        [
            SHARED
            + emission_holding('Variable("w")', "src")
            + 'Copy Emission "src" "dst"\n',
            emission_holding('Variable("w")', "src")
            + 'Copy Emission "src" "dst"\n'
            + SHARED,
        ],
        ids=["declared_before", "declared_after"],
    )
    def test_the_copy_shares_the_nodes_it_references(self, read_deck, define):
        parser = read_deck(define)
        shared = parser.nodes.variables["w"]

        assert parser.nodes.emissions["src"].global_warming_potential is shared
        assert parser.nodes.emissions["dst"].global_warming_potential is shared

    # input:    | Fuel "src" { ... set_ttw("co2", 2.75) }
    #           | Copy Fuel "src" "dst"
    # expected: -> both fuels read ttw["co2"] = 2.75
    def test_a_command_queued_on_the_source_runs_on_the_copy(self, read_deck):
        parser = read_deck(CO2 + _fuel("src", 2.75) + 'Copy Fuel "src" "dst"\n')

        assert parser.nodes.fuels["src"].ttw["co2"].get() == 2.75
        assert parser.nodes.fuels["dst"].ttw["co2"].get() == 2.75

    # input:    | Fuel "src" { ... set_ttw("co2", <2 * Variable("w")>) }
    #           | Copy Fuel "src" "dst"
    # expected: -> each fuel holds its own Expression bound to itself;
    #              "dst" reads 2 * 0.5 = 1.0
    def test_an_expression_input_is_copied_and_bound_to_each_node(self, read_deck):
        # the walk binds an expression in place to the node holding it, so a
        # shared one would stay bound to whichever node it reached first
        define = SHARED + CO2 + _fuel("src", '<2 * Variable("w")>')
        parser = read_deck(define + 'Copy Fuel "src" "dst"\n')
        source = parser.nodes.fuels["src"]
        copied = parser.nodes.fuels["dst"]

        assert isinstance(copied.ttw["co2"], Expression)
        assert source.ttw["co2"] is not copied.ttw["co2"]
        assert source.ttw["co2"]._node is source
        assert copied.ttw["co2"]._node is copied
        # 2 * 0.5
        assert copied.ttw["co2"].get() == 1.0

    # input:    | Copy Variable "v" "dst"   (v only in the library, Value = 3.0)
    # expected: -> only "dst" is registered and reads 3.0; "v" is not kept
    def test_a_source_pulled_from_the_library_is_removed_after_the_copy(
        self, tmp_path, read_deck
    ):
        data_dir = write_library(
            tmp_path / "data", "Variable", installation={"v": DEFAULT}
        )
        define = 'Copy Variable "v" "dst"\n' + emission_holding('Variable("dst")')

        parser = read_deck(define, data_dir=data_dir)

        assert set(parser.nodes.variables) == {"dst"}
        assert parser.nodes.variables["dst"].get() == 3.0

    # input:    | Variable "w" { Value = 0.5 }
    #           | Variable "x" { Value = 1.0 }
    #           | Copy Variable "w" "x"
    # expected: -> DeckKeywordError "Unable to add Variable("x"), the name is
    #              already in use by a different node."
    def test_a_target_name_in_use_is_rejected(self, read_deck):
        define = SHARED + variable("x", Value=1.0) + 'Copy Variable "w" "x"\n'

        with pytest.raises(
            DeckKeywordError,
            match=(
                r"define\.inc', line 11: Unable to add Variable\(\"x\"\), the name "
                r"is already in use by a different node\.$"
            ),
        ):
            read_deck(define)

    # input:    | Copy ModelDefinition "a" "b"
    # expected: -> DeckKeywordError "'ModelDefinition' cannot be copied."
    def test_a_general_node_type_is_rejected(self, read_deck):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"^Error in deck file, line 1, include file '.*define\.inc', line 5: "
                rf"'{MODEL_DEFINITION}' cannot be copied\.$"
            ),
        ):
            read_deck(f'Copy {MODEL_DEFINITION} "a" "b"\n')


class TestImport:
    # input:    | Import Variable "v"   (library file holds Value = 3.0)
    # expected: -> Variable "v" is registered and reads 3.0
    def test_an_import_pulls_the_named_default(self, tmp_path, read_deck):
        data_dir = write_library(
            tmp_path / "data", "Variable", installation={"v": DEFAULT}
        )
        define = 'Import Variable "v"\n' + emission_holding('Variable("v")')

        parser = read_deck(define, data_dir=data_dir)

        assert parser.nodes.variables["v"].get() == 3.0

    # input:    | Import Variable "a*"
    #           | library: user a1 = 10; installation a1 = 1, a2 = 2, b = 3
    # expected: -> {"a1": 10.0, "a2": 2.0}; the user a1 wins and "b" does not match
    def test_a_wildcard_import_pulls_every_match_user_branch_first(
        self, tmp_path, read_deck
    ):
        data_dir = write_library(
            tmp_path / "data",
            "Variable",
            user={"a1": variable("a1", Value=10.0)},
            installation={
                "a1": variable("a1", Value=1.0),
                "a2": variable("a2", Value=2.0),
                "b": variable("b", Value=3.0),
            },
        )
        define = (
            'Import Variable "a*"\n'
            + emission_holding('Variable("a1")', "e1")
            + emission_holding('Variable("a2")', "e2")
        )

        parser = read_deck(define, data_dir=data_dir)
        values = {name: node.get() for name, node in parser.nodes.variables.items()}

        assert values == {"a1": 10.0, "a2": 2.0}

    # input:    | Variable "v" { Value = 1.0 }
    #           | Import Variable "v"
    # expected: -> DeckKeywordError "Unable to add Variable("v"), the name is
    #              already in use ..."
    def test_an_import_of_a_name_in_use_is_rejected(self, tmp_path, read_deck):
        data_dir = write_library(
            tmp_path / "data", "Variable", installation={"v": DEFAULT}
        )

        with pytest.raises(
            DeckKeywordError,
            match=r'Unable to add Variable\("v"\), the name is already in use',
        ):
            read_deck(variable(Value=1.0) + 'Import Variable "v"\n', data_dir=data_dir)

    # input:    | Import Variable "z*"   (the library holds only "v")
    # expected: -> DeckKeywordError "No Variable defaults matching 'z*' found in
    #              user or installation folders."
    def test_a_wildcard_import_without_a_match_is_rejected(self, tmp_path, read_deck):
        data_dir = write_library(
            tmp_path / "data", "Variable", installation={"v": DEFAULT}
        )

        with pytest.raises(
            DeckKeywordError,
            match=(
                r"define\.inc', line 5: No Variable defaults matching 'z\*' found "
                r"in user or installation folders\.$"
            ),
        ):
            read_deck('Import Variable "z*"\n', data_dir=data_dir)

    # input:    | Import Variable "a*"   (no assumptions directory given)
    # expected: -> DeckKeywordError "Wildcard Import is requested but no
    #              assumptions directory is specified."
    def test_a_wildcard_import_without_an_assumptions_directory_is_rejected(
        self, write_deck
    ):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"^Error in deck file, line 1: Wildcard Import is requested but no "
                r"assumptions directory is specified\."
            ),
        ):
            Parser().read_deck(write_deck('Import Variable "a*"\n'))


# input:    | EVENTS: Start
#           | Copy Variable "v" "w"
#           | End
# expected: -> DeckKeywordError "Unable to copy new nodes outside DEFINE."
#              (Import Variable "v" gives "Unable to import new nodes ...")
@pytest.mark.parametrize(
    ("statement", "action"),
    [('Copy Variable "v" "w"\n', "copy"), ('Import Variable "v"\n', "import")],
    ids=["copy", "import"],
)
def test_a_statement_creating_nodes_in_events_is_rejected(
    tmp_path, read_deck, statement, action
):
    data_dir = write_library(tmp_path / "data", "Variable", installation={"v": DEFAULT})
    define = variable(Value=1.0) + emission_holding('Variable("v")')
    parser = read_deck(
        define, events="Start\n" + statement + "End\n", data_dir=data_dir
    )

    with pytest.raises(
        DeckKeywordError,
        match=rf"events\.inc', line 2: Unable to {action} new nodes outside DEFINE\.$",
    ):
        parser.read_events(parser.dates[0])


class TestLoad:
    @staticmethod
    def _module_tree(tmp_path, **branches):
        for branch, content in branches.items():
            directory = tmp_path / "data" / "modules" / branch
            directory.mkdir(parents=True)
            # the Load name is CamelCase, its file snake_case
            (directory / "my_module.inc").write_text(content)
        return tmp_path / "data"

    # input:    | DEFINE { Load MyModule }
    #           | user my_module.inc sets v = 5.0, installation sets v = 1.0
    # expected: -> Variable "v" reads 5.0, from the user module
    def test_load_reads_the_user_module_over_the_installation_one(self, tmp_path):
        data_dir = self._module_tree(
            tmp_path,
            user=variable(Value=5.0) + emission_holding('Variable("v")'),
            installation=variable(Value=1.0) + emission_holding('Variable("v")'),
        )
        deck = _write_nav(tmp_path, "    Load MyModule\n")

        parser = Parser()
        parser.read_deck(deck, data_dir=data_dir)

        assert parser.nodes.variables["v"].get() == 5.0

    # input:    | DEFINE { Load MyModule }   (only the installation module exists)
    # expected: -> Variable "v" reads 1.0, from the installation module
    def test_load_falls_back_to_the_installation_module(self, tmp_path):
        data_dir = self._module_tree(
            tmp_path,
            installation=variable(Value=1.0) + emission_holding('Variable("v")'),
        )
        (tmp_path / "data" / "modules" / "user").mkdir()
        deck = _write_nav(tmp_path, "    Load MyModule\n")

        parser = Parser()
        parser.read_deck(deck, data_dir=data_dir)

        assert parser.nodes.variables["v"].get() == 1.0

    # input:    | DEFINE { Load Missing }
    # expected: -> DeckKeywordError "No module with name 'Missing' was found."
    def test_an_unknown_module_is_rejected(self, tmp_path):
        data_dir = self._module_tree(tmp_path, user="", installation="")
        deck = _write_nav(tmp_path, "    Load Missing\n")

        with pytest.raises(
            DeckKeywordError, match=r"^No module with name 'Missing' was found\.$"
        ):
            Parser().read_deck(deck, data_dir=data_dir)

    # input:    | DEFINE { Load MyModule }   (no assumptions directory given)
    # expected: -> DeckFormatError "Module 'MyModule' is requested but no
    #              assumptions directory is specified."
    def test_load_without_an_assumptions_directory_is_rejected(self, tmp_path):
        deck = _write_nav(tmp_path, "    Load MyModule\n")

        with pytest.raises(
            DeckFormatError,
            match=(
                r"^Error in deck file, line 3: Module 'MyModule' is requested but "
                r"no assumptions directory is specified\."
            ),
        ):
            Parser().read_deck(deck)
