# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests the command line: up-front path validation and top-level error handling."""

from __future__ import annotations

import argparse
import os
import sys

import pytest

from navigate.app import cli
from navigate.app.cli import ASSUMPTIONS_ENV_VAR, _build_parser, main
from navigate.app.logs import RunLog

# Fails at parse time with a caret-pointed DeckFormatError, before any simulation work.
GARBLED_DECK = "DEFINE {\n    garbage\n}\n"

# Node bodies whose value the model rejects once the deck itself has parsed.
REJECTED_ATTRIBUTE_VALUE = 'Vessel "v" {\n    Capex = FLAT\n}\n'
# the required attributes are checked before the commands run
REJECTED_COMMAND_VALUE = (
    'Fleet "fleet" {\n'
    "    InitialVessels = 1\n"
    "    InterFuelSensitivity = 1.0\n"
    "    IntraFuelSensitivity = 1.0\n"
    "    set_operational_saving_sea(PROPULSION, 2.0)\n"
    "}\n"
)


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    """Isolate tests from the caller's env var."""
    monkeypatch.delenv(ASSUMPTIONS_ENV_VAR, raising=False)


def _write_deck(tmp_path, define_body):
    (tmp_path / "define.inc").write_text(
        'ModelDefinition {\n    StartDate = "01/01/2025"\n}\n' + define_body
    )
    (tmp_path / "events.inc").write_text('Start\nDate "01-01-2026"\nEnd\n')

    deck = tmp_path / "deck.nav"
    deck.write_text(
        'DEFINE { Include "./define.inc" }\nEVENTS { Include "./events.inc" }\n'
    )
    return deck


def _run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["navigate", *[str(a) for a in argv]])
    return main()


def _assert_usage_error(monkeypatch, capsys, *argv):
    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, *argv)

    assert exc_info.value.code == 2
    return capsys.readouterr().err


def _missing_deck(tmp_path, monkeypatch):
    return [tmp_path / "nope.nav"]


def _directory_as_deck(tmp_path, monkeypatch):
    return [tmp_path]


def _wrong_extension(tmp_path, monkeypatch):
    deck = tmp_path / "deck.txt"
    deck.write_text(GARBLED_DECK)
    return [deck]


def _missing_filename(tmp_path, monkeypatch):
    return []


def _bad_data_dir(tmp_path, monkeypatch):
    deck = tmp_path / "deck.nav"
    deck.write_text(GARBLED_DECK)
    return [deck, "-d", tmp_path / "no_such_dir"]


def _bad_data_dir_from_env_var(tmp_path, monkeypatch):
    deck = tmp_path / "deck.nav"
    deck.write_text(GARBLED_DECK)
    monkeypatch.setenv(ASSUMPTIONS_ENV_VAR, str(tmp_path / "no_such_dir"))
    return [deck]


class TestArgumentValidation:
    @pytest.mark.parametrize(
        ("build_argv", "expected"),
        [
            pytest.param(_missing_deck, ["not found"], id="missing_deck"),
            pytest.param(_directory_as_deck, ["directory"], id="directory_as_deck"),
            pytest.param(_wrong_extension, [".nav"], id="wrong_extension"),
            pytest.param(
                _missing_filename,
                ["the following arguments are required"],
                id="missing_filename",
            ),
            pytest.param(
                _bad_data_dir, ["-d/--data-dir", "no_such_dir"], id="bad_data_dir"
            ),
            pytest.param(
                _bad_data_dir_from_env_var,
                [ASSUMPTIONS_ENV_VAR],
                id="bad_data_dir_from_env_var",
            ),
        ],
    )
    def test_rejects_invalid_argv(
        self, monkeypatch, capsys, tmp_path, build_argv, expected
    ):
        argv = build_argv(tmp_path, monkeypatch)
        err = _assert_usage_error(monkeypatch, capsys, *argv)
        for substring in expected:
            assert substring in err


class TestTopLevelErrorHandling:
    def test_deck_parse_error_shows_caret_message_no_traceback(
        self, monkeypatch, capsys, tmp_path
    ):
        deck = tmp_path / "deck.nav"
        deck.write_text(GARBLED_DECK)

        assert _run_main(monkeypatch, deck) == 1

        captured = capsys.readouterr()
        assert "^" in captured.err
        assert "Unexpected" in captured.err
        assert "Traceback" not in captured.err
        assert "Traceback" not in captured.out

    def test_deck_parse_error_debug_shows_traceback(
        self, monkeypatch, capsys, tmp_path
    ):
        deck = tmp_path / "deck.nav"
        deck.write_text(GARBLED_DECK)

        assert _run_main(monkeypatch, deck, "-l", "DEBUG") == 1
        assert "Traceback" in capsys.readouterr().err

    def test_deck_parse_error_traceback_logged_at_every_level(
        self, monkeypatch, capsys, tmp_path
    ):
        deck = tmp_path / "deck.nav"
        deck.write_text(GARBLED_DECK)

        assert _run_main(monkeypatch, deck) == 1

        log = (tmp_path / "deck.log").read_text()
        assert "Fatal error" in log
        assert "Traceback" in log

    @pytest.mark.parametrize(
        ("define_body", "expected"),
        [
            pytest.param(
                REJECTED_ATTRIBUTE_VALUE, "attribute 'Capex'", id="attribute_value"
            ),
            pytest.param(
                REJECTED_COMMAND_VALUE,
                "'set_operational_saving_sea'",
                id="command_value",
            ),
        ],
    )
    def test_rejected_deck_value_shows_one_line_no_traceback(
        self, monkeypatch, capsys, tmp_path, define_body, expected
    ):
        deck = _write_deck(tmp_path, define_body)

        assert _run_main(monkeypatch, deck) == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert expected in captured.err
        assert "Traceback" not in captured.err
        assert "Traceback" not in captured.out

    def test_keyboard_interrupt_exits_130(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / "deck.nav"
        deck.write_text(GARBLED_DECK)

        def _interrupt(args, run_log):
            raise KeyboardInterrupt

        monkeypatch.setattr(cli, "_dispatch", _interrupt)

        assert _run_main(monkeypatch, deck) == 130
        assert "Interrupted" in capsys.readouterr().err


class TestPreamble:
    @pytest.mark.parametrize("profile", [False, True], ids=["plain", "profile"])
    def test_dispatch_prints_the_preamble_once(self, monkeypatch, tmp_path, profile):
        preambles = []
        monkeypatch.setattr(cli, "print_preamble", lambda: preambles.append(1))
        monkeypatch.setattr(cli, "run_deck", lambda *args, **kwargs: None)
        args = argparse.Namespace(
            filename=tmp_path / "deck.nav",
            log_level="INFO",
            profile=profile,
            suppress_plots=False,
            results=None,
            data_dir=None,
            solver=None,
        )

        with RunLog(args.filename, args.log_level) as run_log:
            assert cli._dispatch(args, run_log) == 0

        assert len(preambles) == 1


class TestWorkingDirectory:
    def test_includes_resolve_against_deck_dir_without_changing_cwd(
        self, monkeypatch, capsys, tmp_path
    ):
        # The deck-relative include must resolve against the deck directory even
        # though the process CWD is elsewhere, and reading the deck must not
        # change the CWD (the deck is rejected later for lacking an EVENTS block).
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "x.inc").write_text("# empty include\n")
        deck = tmp_path / "deck.nav"
        deck.write_text('DEFINE {\n    Include "sub/x.inc"\n}\n')

        cwd = os.getcwd()
        assert _run_main(monkeypatch, deck) == 1

        captured = capsys.readouterr()
        assert "not found" not in captured.err
        assert "EVENTS" in captured.err
        assert os.getcwd() == cwd


class TestSolverOverride:
    @pytest.mark.parametrize("choice", ["auto", "gurobi", "highs"])
    def test_cli_choice_reaches_the_arguments(self, tmp_path, choice):
        deck_path = tmp_path / "deck.nav"
        args = _build_parser().parse_args([str(deck_path), "--solver", choice])

        assert args.solver == choice

    def test_unknown_choice_exits_with_usage_error(self, capsys, tmp_path):
        deck_path = tmp_path / "deck.nav"

        with pytest.raises(SystemExit) as excinfo:
            _build_parser().parse_args([str(deck_path), "--solver", "bogus"])

        assert excinfo.value.code == 2
        assert "invalid choice: 'bogus'" in capsys.readouterr().err
