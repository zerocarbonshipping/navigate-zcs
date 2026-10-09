# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests the run log: its warning ledger, and its lifecycle on the root logger."""

from __future__ import annotations

import logging

import pytest

from navigate.app.logs import RunLog

# 4 warnings, 2 of them distinct: the first logged 3 times, the second once
WARNINGS = ["first warning", "second warning", "first warning", "first warning"]


def test_ledger_writes_each_warning_once_and_counts_every_repeat(tmp_path, caplog):
    emitter = logging.getLogger("navigate.test")

    with RunLog(tmp_path / "deck.nav", "INFO") as run_log:
        for message in WARNINGS:
            emitter.warning(message)
        for _ in range(2):
            emitter.info("progress")
        run_log.log_summary()

    log = (tmp_path / "deck.log").read_text(encoding="utf-8")
    assert log.count("[WARNING] navigate.test: first warning\n") == 1
    assert log.count("[WARNING] navigate.test: second warning\n") == 1
    assert log.count("[INFO] navigate.test: progress\n") == 2

    summary, digest = (r for r in caplog.records if r.name == "navigate.app.logs")
    counts = dict(zip(summary.table["Level"], summary.table["Count"], strict=True))
    assert counts["WARNING"] == 4
    assert digest.getMessage() == (
        "Unique warnings (2 unique, 2 duplicates suppressed):\n"
        "  1. (3x) first warning\n"
        "  2. second warning"
    )


def test_exit_restores_the_root_logger_and_closes_the_file(tmp_path):
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level

    with RunLog(tmp_path / "deck.nav", "DEBUG"):
        (handler,) = (h for h in root.handlers if h not in handlers)
        stream = handler.stream
        assert root.level == logging.DEBUG

    assert root.handlers == handlers
    assert root.level == level
    assert stream.closed


def test_invalid_level_raises_before_the_log_opens(tmp_path):
    root = logging.getLogger()
    handlers = list(root.handlers)

    with pytest.raises(ValueError, match="'FOO'"), RunLog(tmp_path / "deck.nav", "FOO"):
        pass

    assert not (tmp_path / "deck.log").exists()
    assert root.handlers == handlers
