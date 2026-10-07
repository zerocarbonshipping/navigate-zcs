# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests the run sequence of a deck: the order of a date's heading, events and step."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import numpy as np
import pytest

from navigate.driver import run

# a start date before 1970 with a yearly step landing on 1970-01-01, continuing past it
DATELINE = np.array(
    ["1969-01-01", "1970-01-01", "1971-01-01", "1972-01-01"], dtype="datetime64[D]"
)


class _HeadingHandler(logging.Handler):
    """Append each heading record to the shared list of calls."""

    def __init__(self, calls):
        super().__init__()
        self.calls = calls

    def emit(self, record):
        if getattr(record, "heading", False):
            self.calls.append(("heading",))


@pytest.fixture
def calls(monkeypatch, caplog):
    """Run against a stub parser and model, recording headings, events and steps."""
    calls = []
    parser = SimpleNamespace(
        nodes=None,
        general_nodes=None,
        dates=DATELINE,
        read_deck=lambda path, data_dir=None: None,
        includes_necessary_information=lambda: None,
        read_events=lambda date: calls.append(("events", date)),
    )
    results = SimpleNamespace(nodes=SimpleNamespace(reports={}, plots={}))
    simulation = SimpleNamespace(
        initialize=lambda: None,
        step=lambda date: calls.append(("step", date)),
        finish=lambda: results,
    )
    monkeypatch.setattr(run, "Parser", lambda: parser)
    monkeypatch.setattr(run, "Simulation", lambda *args: simulation)

    handler = _HeadingHandler(calls)
    caplog.set_level(logging.INFO, logger=run.logger.name)
    run.logger.addHandler(handler)

    yield calls

    run.logger.removeHandler(handler)


def test_each_date_logs_its_heading_then_applies_its_events_then_steps(calls, tmp_path):
    run.run_deck(tmp_path / "deck.nav", plots=False)

    expected = [
        call
        for date in DATELINE
        for call in (("heading",), ("events", date), ("step", date))
    ]
    assert calls == expected
