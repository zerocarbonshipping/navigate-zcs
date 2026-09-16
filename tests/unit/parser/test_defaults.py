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
    # an Emission is a top-level node, so the referenced Variable is never pruned
    return f"""
Emission "{emission}" {{
    GlobalWarmingPotential = Variable("{variable}")
}}
"""


MODEL_DEFINITION = """
ModelDefinition {
    StartDate = "01-01-2026"
}
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


def _write_deck(tmp_path, define, events=None):
    (tmp_path / "define.inc").write_text(MODEL_DEFINITION + define)
    events_block = "EVENTS { }\n"
    if events is not None:
        (tmp_path / "events.inc").write_text(events)
        events_block = 'EVENTS { Include "events.inc" }\n'

    deck = tmp_path / "deck.nav"
    deck.write_text('DEFINE { Include "define.inc" }\n' + events_block)
    return deck


def _read_deck(tmp_path, define, *, installation=None, user=None, events=None):
    data_dir = tmp_path / "data"
    # mirror the shipped library: both branches carry a directory per node type
    for branch, files in (("user", user), ("installation", installation)):
        directory = data_dir / "defaults" / branch / "Variable"
        directory.mkdir(parents=True)
        for stem, content in (files or {}).items():
            (directory / f"{stem}.inc").write_text(content)

    parser = Parser()
    parser.read_deck(_write_deck(tmp_path, define, events), data_dir=data_dir)
    return parser


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
        self, tmp_path, define, expected
    ):
        parser = _read_deck(tmp_path, define, installation={"v": DECOY})
        variable = parser.nodes.variables["v"]

        assert parser.nodes.emissions["e"].global_warming_potential is variable
        assert variable.get() == expected

    @pytest.mark.parametrize(
        "define",
        [HOST, HOST + 'Import Variable "v"\n', HOST + 'Import Variable "v*"\n'],
        ids=["reference", "import_after_reference", "wildcard_import"],
    )
    def test_undeclared_name_binds_to_the_library_node(self, tmp_path, define):
        parser = _read_deck(tmp_path, define, installation={"v": DEFAULT})
        variable = parser.nodes.variables["v"]

        assert parser.nodes.emissions["e"].global_warming_potential is variable
        assert variable.get() == 3.0

    def test_command_argument_reference_pulls_its_default(self, tmp_path):
        parser = _read_deck(tmp_path, COMMAND_HOST, installation={"v": DEFAULT})

        assert parser.nodes.variables["v"].get() == 3.0


class TestDefaultPrecedence:
    def test_user_branch_shadows_installation_branch(self, tmp_path):
        parser = _read_deck(
            tmp_path,
            HOST,
            user={"v": _variable(Value=5.0)},
            installation={"v": DEFAULT},
        )

        assert parser.nodes.variables["v"].get() == 5.0

    def test_user_file_overlays_the_installation_node_of_the_same_name(self, tmp_path):
        # the Import inside the user file for v reads the installation v instead
        # of re-entering the user file: 2.0 * 3.0
        parser = _read_deck(
            tmp_path, HOST, user={"v": OVERLAY}, installation={"v": DEFAULT}
        )

        assert parser.nodes.variables["v"].get() == 6.0

    def test_overlay_survives_an_import_of_another_library_node(self, tmp_path):
        # pulling y must not cost the user file its own overlay route: the
        # self-Import still reaches the installation v, so 2.0 * 3.0 again
        parser = _read_deck(
            tmp_path,
            HOST,
            user={"v": OVERLAY_AFTER_IMPORT},
            installation={"v": DEFAULT, "y": _variable("y", Value=1.0)},
        )

        assert parser.nodes.variables["v"].get() == 6.0


class TestCopyFromDefault:
    def test_source_is_removed_after_the_copy(self, tmp_path):
        define = 'Copy Variable "v" "dst"\n' + _host("dst")

        parser = _read_deck(tmp_path, define, installation={"v": DEFAULT})

        assert set(parser.nodes.variables) == {"dst"}
        assert parser.nodes.variables["dst"].get() == 3.0

    def test_separate_reference_pulls_the_source_again(self, tmp_path):
        define = 'Copy Variable "v" "dst"\n' + _host("v") + _host("dst", emission="e2")

        parser = _read_deck(tmp_path, define, installation={"v": DEFAULT})
        source = parser.nodes.variables["v"]
        copied = parser.nodes.variables["dst"]

        assert set(parser.nodes.variables) == {"v", "dst"}
        assert parser.nodes.emissions["e"].global_warming_potential is source
        assert parser.nodes.emissions["e2"].global_warming_potential is copied
        assert source is not copied


class TestUnresolvableReference:
    def test_missing_default_names_the_type_and_name(self, tmp_path):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r'Variable\("v"\) is referenced but not found in either the deck '
                r"or the default location of Variable"
            ),
        ):
            _read_deck(tmp_path, HOST)

    @pytest.mark.parametrize(
        "content",
        [_variable("w", Value=1.0), 'Emission "v" { }\n'],
        ids=["wrong_name", "wrong_type"],
    )
    def test_file_without_the_requested_node_is_rejected(self, tmp_path, content):
        with pytest.raises(
            DeckKeywordError,
            match=(
                r"A file with name 'v' was found, but not containing a node with "
                r"type 'Variable'"
            ),
        ):
            _read_deck(tmp_path, HOST, installation={"v": content})

    def test_reference_without_an_assumptions_directory_is_rejected(self, tmp_path):
        with pytest.raises(
            DeckKeywordError,
            match=r"User or Installation Default 'v' is requested but not specified",
        ):
            Parser().read_deck(_write_deck(tmp_path, HOST))


class TestEventsTarget:
    def test_undeclared_target_is_rejected_instead_of_pulled(self, tmp_path):
        # the library holds the target, so success would mean EVENTS created a
        # node from it
        parser = _read_deck(tmp_path, "", installation={"v": DEFAULT}, events=EVENTS)

        with pytest.raises(
            DeckKeywordError, match="Unable to define new nodes outside DEFINE"
        ):
            parser.progress_timeline()
