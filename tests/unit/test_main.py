# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the CLI entry point: up-front path validation and top-level error handling."""
import logging
import os
import sys

import pytest

from navigate.__main__ import ASSUMPTIONS_ENV_VAR, main
from navigate.output.plot_data import PlotData

# Fails at parse time with a caret-pointed DeckFormatError, before any simulation work.
GARBLED_DECK = 'DEFINE {\n    garbage\n}\n'


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
    monkeypatch.setattr(sys, 'argv', ['navigate', *[str(a) for a in argv]])
    return main()


def _assert_usage_error(monkeypatch, capsys, *argv):
    with pytest.raises(SystemExit) as exc_info:
        _run_main(monkeypatch, *argv)

    assert exc_info.value.code == 2
    return capsys.readouterr().err


class TestArgumentValidation:

    def test_missing_deck_file_exits_2(self, monkeypatch, capsys, tmp_path):
        err = _assert_usage_error(monkeypatch, capsys, tmp_path / 'nope.nav')
        assert 'not found' in err

    def test_directory_as_deck_path_exits_2(self, monkeypatch, capsys, tmp_path):
        err = _assert_usage_error(monkeypatch, capsys, tmp_path)
        assert 'directory' in err

    def test_wrong_extension_exits_2(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.txt'
        deck.write_text(GARBLED_DECK)

        err = _assert_usage_error(monkeypatch, capsys, deck)
        assert ".nav" in err

    def test_missing_filename_exits_2(self, monkeypatch, capsys):
        err = _assert_usage_error(monkeypatch, capsys)
        assert 'filename is required' in err

    def test_bad_data_dir_exits_2(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.nav'
        deck.write_text(GARBLED_DECK)

        err = _assert_usage_error(monkeypatch, capsys, deck, '-d', tmp_path / 'no_such_dir')
        assert '-d/--data-dir' in err
        assert 'no_such_dir' in err

    def test_bad_data_dir_from_env_var_exits_2(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.nav'
        deck.write_text(GARBLED_DECK)
        monkeypatch.setenv(ASSUMPTIONS_ENV_VAR, str(tmp_path / 'no_such_dir'))

        err = _assert_usage_error(monkeypatch, capsys, deck)
        assert ASSUMPTIONS_ENV_VAR in err

    def test_missing_replot_path_exits_2(self, monkeypatch, capsys, tmp_path):
        err = _assert_usage_error(monkeypatch, capsys, '--replot', tmp_path / 'nope')
        assert '--replot' in err

    def test_replot_include_wrong_extension_exits_2(self, monkeypatch, capsys, tmp_path):
        plots = tmp_path / 'plots.txt'
        plots.write_text('')

        err = _assert_usage_error(monkeypatch, capsys, '--replot', tmp_path, plots)
        assert ".inc" in err


class TestTopLevelErrorHandling:

    def test_deck_parse_error_shows_caret_message_no_traceback(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.nav'
        deck.write_text(GARBLED_DECK)

        assert _run_main(monkeypatch, deck) == 1

        captured = capsys.readouterr()
        assert '^' in captured.err
        assert 'Unexpected' in captured.err
        assert 'Traceback' not in captured.err
        assert 'Traceback' not in captured.out

    def test_deck_parse_error_debug_shows_traceback(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.nav'
        deck.write_text(GARBLED_DECK)

        assert _run_main(monkeypatch, deck, '-l', 'DEBUG') == 1
        assert 'Traceback' in capsys.readouterr().err

    def test_deck_parse_error_traceback_logged_at_every_level(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.nav'
        deck.write_text(GARBLED_DECK)

        assert _run_main(monkeypatch, deck) == 1

        log = (tmp_path / 'deck.log').read_text()
        assert 'Fatal error' in log
        assert 'Traceback' in log

    def test_replot_bad_pickle_no_traceback(self, monkeypatch, capsys, tmp_path):
        (tmp_path / 'plot_data.pkl').write_bytes(b'not a gzip file')

        assert _run_main(monkeypatch, '--replot', tmp_path) == 1

        captured = capsys.readouterr()
        assert 'Error:' in captured.err
        assert 'Traceback' not in captured.err

    def test_replot_no_plot_configs_no_traceback(self, monkeypatch, capsys, tmp_path):
        PlotData().save(str(tmp_path))

        assert _run_main(monkeypatch, '--replot', tmp_path) == 1

        captured = capsys.readouterr()
        assert 'no plot configurations' in captured.err
        assert 'Traceback' not in captured.err

    def test_keyboard_interrupt_exits_130(self, monkeypatch, capsys, tmp_path):
        deck = tmp_path / 'deck.nav'
        deck.write_text(GARBLED_DECK)

        def _interrupt(args):
            raise KeyboardInterrupt

        monkeypatch.setattr('navigate.__main__._dispatch', _interrupt)

        assert _run_main(monkeypatch, deck) == 130
        assert 'Interrupted' in capsys.readouterr().err


class TestWorkingDirectory:

    def test_includes_resolve_against_deck_dir_without_changing_cwd(self, monkeypatch, capsys, tmp_path):
        # The deck-relative include must resolve against the deck directory even
        # though the process CWD is elsewhere, and reading the deck must not
        # change the CWD (the deck is rejected later for lacking an EVENTS block).
        (tmp_path / 'sub').mkdir()
        (tmp_path / 'sub' / 'x.inc').write_text('# empty include\n')
        deck = tmp_path / 'deck.nav'
        deck.write_text('DEFINE {\n    Include "sub/x.inc"\n}\n')

        cwd = os.getcwd()
        assert _run_main(monkeypatch, deck) == 1

        captured = capsys.readouterr()
        assert 'not found' not in captured.err
        assert 'EVENTS' in captured.err
        assert os.getcwd() == cwd
