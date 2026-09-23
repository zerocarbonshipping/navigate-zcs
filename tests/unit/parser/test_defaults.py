# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Resolve node references against the default library through Parser.read_deck.

Which node a reference binds to, user-over-installation precedence, the
from-default Copy idiom, and the errors for references that cannot be resolved.
"""

from __future__ import annotations

import pytest

from navigate.exceptions import DeckKeywordError
from navigate.parser.parser import Parser


def _variable(name="v", **attributes):
    body = "".join(f"    {key} = {value}\n" for key, value in attributes.items())
    return f'Variable "{name}" {{\n{body}}}\n'


def _host(variable, emission="e"):
    # an Emission is a top-level node, so the referenced Variable is never
    # pruned (see the conftest module docstring)
    return f"""
Emission "{emission}" {{
    GlobalWarmingPotential = Variable("{variable}")
}}
"""


HOST = _host("v")
DEFAULT = _variable(Value=3.0)
# a library node whose multiplier makes an unintended pull visible as 30.0
DECOY = _variable(Value=3.0, Multiplier=10.0)
OVERLAY = 'Import Variable "v"\n' + _variable(Multiplier=2.0)
# the same overlay, behind a pull of an unrelated library node
OVERLAY_AFTER_IMPORT = 'Import Variable "y"\n' + OVERLAY
COMMAND_HOST = """
Emission "co2" { }

Fuel "oil" {
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
    set_ttw("co2", Variable("v"))
}
"""
EVENTS = """
Start

Variable "v" {
    Value = 2.0
}

End
"""


@pytest.fixture
def read_library_deck(tmp_path, read_deck):
    """Read a deck against a synthesised two-branch default library."""

    def read(define, *, installation=None, user=None, events=None):
        data_dir = tmp_path / "data"
        # mirror the shipped library: both branches carry a directory per node type
        for branch, files in (("user", user), ("installation", installation)):
            directory = data_dir / "defaults" / branch / "Variable"
            directory.mkdir(parents=True)
            for stem, content in (files or {}).items():
                (directory / f"{stem}.inc").write_text(content)

        return read_deck(define, events=events, data_dir=data_dir)

    return read


class TestReferenceResolution:
    @pytest.mark.parametrize(
        ("define", "expected"),
        [
            (HOST + _variable(Value=1.0), 1.0),
            (HOST + _variable("src", Value=4.0) + 'Copy Variable "src" "v"\n', 4.0),
        ],
        ids=["deck_declaration", "copy_target"],
    )
    def test_declaration_after_the_reference_shadows_the_library(
        self, read_library_deck, define, expected
    ):
        parser = read_library_deck(define, installation={"v": DECOY})
        variable = parser.nodes.variables["v"]

        assert parser.nodes.emissions["e"].global_warming_potential is variable
        assert variable.get() == expected

    @pytest.mark.parametrize(
        "define",
        [HOST, HOST + 'Import Variable "v"\n', HOST + 'Import Variable "v*"\n'],
        ids=["reference", "import_after_reference", "wildcard_import"],
    )
    def test_undeclared_name_binds_to_the_library_node(self, read_library_deck, define):
        parser = read_library_deck(define, installation={"v": DEFAULT})
        variable = parser.nodes.variables["v"]

        assert parser.nodes.emissions["e"].global_warming_potential is variable
        assert variable.get() == 3.0

    def test_command_argument_reference_pulls_its_default(self, read_library_deck):
        parser = read_library_deck(COMMAND_HOST, installation={"v": DEFAULT})

        assert parser.nodes.variables["v"].get() == 3.0

    def test_bounds_of_an_overwritten_reference_stay_on_the_node(
        self, read_library_deck
    ):
        # GlobalWarmingPotential imposes its lower bound when the first assignment
        # is read; the EVENTS reference only keeps the Variable from being pruned
        define = (
            HOST
            + 'Emission "e" { GlobalWarmingPotential = 1.0 }\n'
            + _variable(Value=-2.0)
        )

        parser = read_library_deck(define, events="Start\n" + HOST + "End\n")

        assert parser.nodes.variables["v"].get() == 0.0


class TestDefaultPrecedence:
    def test_user_branch_shadows_installation_branch(self, read_library_deck):
        parser = read_library_deck(
            HOST,
            user={"v": _variable(Value=5.0)},
            installation={"v": DEFAULT},
        )

        assert parser.nodes.variables["v"].get() == 5.0

    def test_user_file_overlays_the_installation_node_of_the_same_name(
        self, read_library_deck
    ):
        # the Import inside the user file for v reads the installation v instead
        # of re-entering the user file: 2.0 * 3.0
        parser = read_library_deck(
            HOST, user={"v": OVERLAY}, installation={"v": DEFAULT}
        )

        assert parser.nodes.variables["v"].get() == 6.0

    def test_overlay_survives_an_import_of_another_library_node(
        self, read_library_deck
    ):
        # pulling y must not cost the user file its own overlay route: the
        # self-Import still reaches the installation v, so 2.0 * 3.0 again
        parser = read_library_deck(
            HOST,
            user={"v": OVERLAY_AFTER_IMPORT},
            installation={"v": DEFAULT, "y": _variable("y", Value=1.0)},
        )

        assert parser.nodes.variables["v"].get() == 6.0


class TestCopyFromDefault:
    def test_source_is_removed_after_the_copy(self, read_library_deck):
        define = 'Copy Variable "v" "dst"\n' + _host("dst")

        parser = read_library_deck(define, installation={"v": DEFAULT})

        assert set(parser.nodes.variables) == {"dst"}
        assert parser.nodes.variables["dst"].get() == 3.0

    @pytest.mark.parametrize(
        "define",
        [
            'Copy Variable "v" "dst"\n' + _host("v") + _host("dst", emission="e2"),
            _host("v") + 'Copy Variable "v" "dst"\n' + _host("dst", emission="e2"),
        ],
        ids=["reference_after_copy", "reference_before_copy"],
    )
    def test_separate_reference_pulls_the_source_again(self, read_library_deck, define):
        parser = read_library_deck(define, installation={"v": DEFAULT})
        source = parser.nodes.variables["v"]
        copied = parser.nodes.variables["dst"]

        assert set(parser.nodes.variables) == {"v", "dst"}
        assert parser.nodes.emissions["e"].global_warming_potential is source
        assert parser.nodes.emissions["e2"].global_warming_potential is copied
        assert source is not copied

    def test_the_copy_takes_over_a_target_the_pulled_file_declares(
        self, read_library_deck
    ):
        # the source file declares the target's name too, so the reference ends
        # on the copy, not on the file's node
        library = {"v": DEFAULT + _variable("dst", Value=9.0)}
        define = _host("dst") + 'Copy Variable "v" "dst"\n'

        parser = read_library_deck(define, installation=library)
        copied = parser.nodes.variables["dst"]

        assert parser.nodes.emissions["e"].global_warming_potential is copied
        assert copied.get() == 3.0

    def test_reference_inside_the_pulled_file_binds_to_the_pulled_again_source(
        self, read_library_deck
    ):
        # the file's own Emission references the source that the copy discards
        library = {"v": DEFAULT + _host("v", emission="inner")}
        define = 'Copy Variable "v" "dst"\n' + _host("dst", emission="e2")

        parser = read_library_deck(define, installation=library)

        assert set(parser.nodes.variables) == {"v", "dst"}
        assert (
            parser.nodes.emissions["inner"].global_warming_potential
            is parser.nodes.variables["v"]
        )


class TestUnresolvableReference:
    @pytest.mark.parametrize(
        "define",
        [HOST, 'Emission "e" { GlobalWarmingPotential = <2 * Variable("v")> }\n'],
        ids=["reference", "expression"],
    )
    def test_missing_default_names_the_type_name_and_location(
        self, read_library_deck, define
    ):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"include file '.*define\.inc', line \d+: "
                r'Variable\("v"\) is referenced but not found in either the deck '
                r"or the default location of Variable"
            ),
        ):
            read_library_deck(define)

    @pytest.mark.parametrize(
        "define",
        [
            'Emission "e" { GlobalWarmingPotential = Foo("x") }\n',
            COMMAND_HOST.replace('Variable("v")', 'Foo("x")'),
        ],
        ids=["attribute", "command_argument"],
    )
    def test_unknown_reference_type_is_a_located_deck_error(
        self, read_library_deck, define
    ):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"include file '.*define\.inc', line \d+: "
                r"'Foo' is not a recognized node type"
            ),
        ):
            read_library_deck(define)

    @pytest.mark.parametrize(
        "library",
        [
            {"installation": {"v": _variable("w", Value=1.0)}},
            {"installation": {"v": 'Emission "v" { }\n'}},
            {"user": {"v": _variable("w", Value=1.0)}},
            # a user file found by name ends the search, so the installation
            # file is no fallback
            {"user": {"v": _variable("w", Value=1.0)}, "installation": {"v": DEFAULT}},
        ],
        ids=["wrong_name", "wrong_type", "user_branch", "user_over_installation"],
    )
    def test_file_without_the_requested_node_is_rejected(
        self, read_library_deck, library
    ):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"include file '.*define\.inc', line \d+: A file with name 'v' was "
                r"found, but not containing a node with type 'Variable'"
            ),
        ):
            read_library_deck(HOST, **library)

    @pytest.mark.parametrize(
        "define",
        ['Import Variable "v"\n', 'Copy Variable "v" "dst"\n'],
        ids=["import", "copy"],
    )
    def test_import_and_copy_reject_a_user_file_without_the_node(
        self, read_library_deck, define
    ):
        with pytest.raises(DeckKeywordError, match=r"A file with name 'v' was found"):
            read_library_deck(define, user={"v": _variable("w", Value=1.0)})

    def test_reference_without_an_assumptions_directory_is_rejected(self, write_deck):
        with pytest.raises(
            DeckKeywordError,
            match=r"User or Installation Default 'v' is requested but not specified",
        ):
            Parser().read_deck(write_deck(HOST))


class TestEventsTarget:
    def test_undeclared_target_is_rejected_instead_of_pulled(self, read_library_deck):
        # the library holds the target, so success would mean EVENTS created a
        # node from it
        parser = read_library_deck("", installation={"v": DEFAULT}, events=EVENTS)

        with pytest.raises(
            DeckKeywordError, match="Unable to define new nodes outside DEFINE"
        ):
            parser.progress_timeline()
