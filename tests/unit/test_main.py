# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the CLI entry point: up-front path validation and top-level error handling."""

from __future__ import annotations

import logging
import os
import sys

import pytest

from navigate.__main__ import ASSUMPTIONS_ENV_VAR, main

# Fails at parse time with a caret-pointed DeckFormatError, before any simulation work.
GARBLED_DECK = "DEFINE {\n    garbage\n}\n"


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch):
    """Isolate tests from the caller's env var and setup_logger's root handlers."""
    monkeypatch.delenv(ASSUMPTIONS_ENV_VAR, raising=False)

    yield

    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)


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


def _missing_replot_path(tmp_path, monkeypatch):
    return ["--replot", tmp_path / "nope"]


def _replot_include_wrong_extension(tmp_path, monkeypatch):
    plots = tmp_path / "plots.txt"
    plots.write_text("")
    return ["--replot", tmp_path, plots]


class TestArgumentValidation:
    @pytest.mark.parametrize(
        "build_argv, expected",
        [
            pytest.param(_missing_deck, ["not found"], id="missing_deck"),
            pytest.param(_directory_as_deck, ["directory"], id="directory_as_deck"),
            pytest.param(_wrong_extension, [".nav"], id="wrong_extension"),
            pytest.param(
                _missing_filename, ["filename is required"], id="missing_filename"
            ),
            pytest.param(
                _bad_data_dir, ["-d/--data-dir", "no_such_dir"], id="bad_data_dir"
            ),
            pytest.param(
                _bad_data_dir_from_env_var,
                [ASSUMPTIONS_ENV_VAR],
                id="bad_data_dir_from_env_var",
            ),
            pytest.param(_missing_replot_path, ["--replot"], id="missing_replot_path"),
            pytest.param(
                _replot_include_wrong_extension,
                [".inc"],
                id="replot_include_wrong_extension",
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

    def test_replot_bad_pickle_no_traceback(self, monkeypatch, capsys, tmp_path):
        (tmp_path / "plot_data.pkl").write_bytes(b"not a gzip file")

        assert _run_main(monkeypatch, "--replot", tmp_path) == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Traceback" not in captured.err

    def test_keyboard_interrupt_exits_130(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / "deck.nav"
        deck.write_text(GARBLED_DECK)

        def _interrupt(args):
            raise KeyboardInterrupt

        monkeypatch.setattr("navigate.__main__._dispatch", _interrupt)

        assert _run_main(monkeypatch, deck) == 130
        assert "Interrupted" in capsys.readouterr().err


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
