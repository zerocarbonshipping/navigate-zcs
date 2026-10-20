# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The statements that bring nodes in from elsewhere: Copy, Import, Load.

Copy duplicates one node's definition as it stands at the Copy, sharing what
it references and running its commands on the copy too. Import pulls named or
globbed nodes from the default library, and Load reads a module; Include is
covered with the sections. Copy and Import are DEFINE-only, and each failure
is a located deck error.
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import emission_holding, variable, write_library
from navigate.core.expression import Expression
from navigate.core.node_type import MODEL_DEFINITION
from navigate.exceptions import DeckError
from navigate.parser.parser import Parser

SHARED = variable("w", Value=0.5)
CO2 = 'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'
DEFAULT = variable(Value=3.0)


def _fuel(name, ttw):
    # the TTW factor is set by a command, which runs once every declaration
    # is read and the dependencies are seeded
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
    def test_a_command_of_the_source_runs_on_the_copy(self, read_deck):
        parser = read_deck(CO2 + _fuel("src", 2.75) + 'Copy Fuel "src" "dst"\n')

        assert parser.nodes.fuels["src"].ttw["co2"].get() == 2.75
        assert parser.nodes.fuels["dst"].ttw["co2"].get() == 2.75

    # input:    | Fuel "src" { ... set_ttw("co2", <2 * Variable("w")>) }
    #           | Copy Fuel "src" "dst"
    # expected: -> each fuel holds its own Expression bound to itself;
    #              "dst" reads 2 * 0.5 = 1.0
    def test_an_expression_input_is_copied_and_bound_to_each_node(self, read_deck):
        # an expression is built per holder, so each node names itself in the
        # errors its expression raises
        define = SHARED + CO2 + _fuel("src", '<2 * Variable("w")>')
        parser = read_deck(define + 'Copy Fuel "src" "dst"\n')
        source = parser.nodes.fuels["src"]
        copied = parser.nodes.fuels["dst"]

        assert isinstance(copied.ttw["co2"], Expression)
        assert source.ttw["co2"] is not copied.ttw["co2"]
        assert source.ttw["co2"]._holder is source
        assert copied.ttw["co2"]._holder is copied
        # 2 * 0.5
        assert copied.ttw["co2"].get() == 1.0

    # input:    | Copy Variable "v" "dst"   (v only in the library, Value = 3.0)
    # expected: -> only "dst" is registered and reads 3.0; "v" is not kept
    def test_a_source_pulled_from_the_library_is_removed_after_the_copy(
        self, tmp_path, read_deck
    ):
        data_dir = write_library(tmp_path / "data", "Variable", {"v": DEFAULT})
        define = 'Copy Variable "v" "dst"\n' + emission_holding('Variable("dst")')

        parser = read_deck(define, data_dir=data_dir)

        assert set(parser.nodes.variables) == {"dst"}
        assert parser.nodes.variables["dst"].get() == 3.0

    # input:    | Variable "w" { Value = 0.5 }
    #           | Variable "x" { Value = 1.0 }
    #           | Copy Variable "w" "x"
    # expected: -> DeckError "Unable to add Variable("x"), the name is already
    #              in use by a different node."
    def test_a_target_name_in_use_is_rejected(self, read_deck):
        define = SHARED + variable("x", Value=1.0) + 'Copy Variable "w" "x"\n'

        with pytest.raises(
            DeckError,
            match=(
                r"define\.inc', line 11: Unable to add Variable\(\"x\"\), the name "
                r"is already in use by a different node\.$"
            ),
        ):
            read_deck(define)

    # input:    | Copy ModelDefinition "a" "b"
    # expected: -> DeckError "'ModelDefinition' cannot be copied."
    def test_a_general_node_type_is_rejected(self, read_deck):
        with pytest.raises(
            DeckError,
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
        data_dir = write_library(tmp_path / "data", "Variable", {"v": DEFAULT})
        define = 'Import Variable "v"\n' + emission_holding('Variable("v")')

        parser = read_deck(define, data_dir=data_dir)

        assert parser.nodes.variables["v"].get() == 3.0

    # input:    | Variable "v" { Value = 1.0 }
    #           | Import Variable "v"
    # expected: -> DeckError "Unable to add Variable("v"), the name is already
    #              in use ..."
    def test_an_import_of_a_name_in_use_is_rejected(self, tmp_path, read_deck):
        data_dir = write_library(tmp_path / "data", "Variable", {"v": DEFAULT})

        with pytest.raises(
            DeckError,
            match=r'Unable to add Variable\("v"\), the name is already in use',
        ):
            read_deck(variable(Value=1.0) + 'Import Variable "v"\n', data_dir=data_dir)

    # input:    | Import Variable "z*"
    # expected: -> DeckError "...define.inc', line 5: Import names one node;
    #              'z*' is a wildcard."
    def test_a_wildcard_import_is_rejected(self, tmp_path, read_deck):
        data_dir = write_library(tmp_path / "data", "Variable", {"v": DEFAULT})

        with pytest.raises(
            DeckError,
            match=(
                r"define\.inc', line 5: Import names one node; 'z\*' is a "
                r"wildcard\.$"
            ),
        ):
            read_deck('Import Variable "z*"\n', data_dir=data_dir)


# input:    | EVENTS: Start
#           | Copy Variable "v" "w"
# expected: -> DeckError "...events.inc', line 2: 'Copy' is not allowed in the
#              EVENTS section." when the deck is read (Import likewise)
@pytest.mark.parametrize(
    ("statement", "keyword"),
    [('Copy Variable "v" "w"\n', "Copy"), ('Import Variable "v"\n', "Import")],
    ids=["copy", "import"],
)
def test_a_statement_creating_nodes_in_events_is_rejected(
    tmp_path, read_deck, statement, keyword
):
    data_dir = write_library(tmp_path / "data", "Variable", {"v": DEFAULT})
    define = variable(Value=1.0) + emission_holding('Variable("v")')

    with pytest.raises(
        DeckError,
        match=(
            rf"events\.inc', line 2: '{keyword}' is not allowed in the EVENTS "
            r"section\.$"
        ),
    ):
        read_deck(define, events="Start\n" + statement, data_dir=data_dir)


class TestLoad:
    @staticmethod
    def _module_tree(tmp_path, content):
        directory = tmp_path / "data" / "modules"
        directory.mkdir(parents=True)
        # the Load name is CamelCase, its file snake_case
        (directory / "my_module.inc").write_text(content)
        return tmp_path / "data"

    # input:    | DEFINE { Load MyModule }
    #           | modules/my_module.inc sets v = 5.0
    # expected: -> Variable "v" reads 5.0, from the snake_case module file
    def test_load_reads_the_snake_case_module_file(self, tmp_path):
        data_dir = self._module_tree(
            tmp_path, variable(Value=5.0) + emission_holding('Variable("v")')
        )
        deck = _write_nav(tmp_path, "    Load MyModule\n")

        parser = Parser()
        parser.read_deck(deck, data_dir=data_dir)

        assert parser.nodes.variables["v"].get() == 5.0

    # input:    | DEFINE { Load Missing }
    # expected: -> DeckError "Error in deck file, line 3: No module with name
    #              'Missing' was found."
    def test_an_unknown_module_is_rejected(self, tmp_path):
        data_dir = self._module_tree(tmp_path, "")
        deck = _write_nav(tmp_path, "    Load Missing\n")

        with pytest.raises(
            DeckError,
            match=(
                r"^Error in deck file, line 3: No module with name 'Missing' was "
                r"found\.$"
            ),
        ):
            Parser().read_deck(deck, data_dir=data_dir)

    # input:    | DEFINE { Load MyModule }   (no assumptions directory given)
    # expected: -> DeckError "Module 'MyModule' is requested but no assumptions
    #              directory is specified."
    def test_load_without_an_assumptions_directory_is_rejected(self, tmp_path):
        deck = _write_nav(tmp_path, "    Load MyModule\n")

        with pytest.raises(
            DeckError,
            match=(
                r"^Error in deck file, line 3: Module 'MyModule' is requested but "
                r"no assumptions directory is specified\."
            ),
        ):
            Parser().read_deck(deck)
