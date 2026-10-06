# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the time-stepping loop of SimulationManager."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import numpy as np
import pytest

from navigate import simulation
from navigate.simulation import SimulationManager

# a start date before 1970 with a yearly step landing on 1970-01-01, continuing past it
TIMELINE_DATES = [
    np.datetime64("1969-01-01"),
    np.datetime64("1970-01-01"),
    np.datetime64("1971-01-01"),
    np.datetime64("1972-01-01"),
]


class _RecordingHandler(logging.Handler):
    """Append each record's kind, time-step index, date and elapsed days to calls."""

    def __init__(self, calls):
        super().__init__()
        self.calls = calls

    def emit(self, record):
        kind = "heading" if getattr(record, "heading", False) else "message"
        self.calls.append((kind, *record.args[:3]))


@pytest.fixture
def calls():
    """Record the simulation logger's INFO records into one ordered list of calls."""
    calls = []
    handler = _RecordingHandler(calls)
    level = simulation.logger.level

    simulation.logger.addHandler(handler)
    simulation.logger.setLevel(logging.INFO)

    yield calls

    simulation.logger.removeHandler(handler)
    simulation.logger.setLevel(level)


def test_run_simulation_logs_heading_then_reads_events_then_steps(calls):
    """
    Each date after the first logs its heading before its events are read.

    The dates cross 1970-01-01, and every one of them is still stepped.
    """
    dateline = np.array(TIMELINE_DATES, dtype="datetime64[D]")

    manager = SimpleNamespace(
        parser=SimpleNamespace(read_events=lambda date: calls.append(("read", date))),
        dateline=dateline,
        _idx=0,
        _computational_time=0.0,
    )
    manager._progress_date_time = lambda date: calls.append(("progress", date))
    manager._perform_time_step = lambda: calls.append(("step",))

    SimulationManager._run_simulation(manager)

    expected = []
    for k, date in enumerate(dateline):
        if k > 0:
            days = (date - dateline[0]) / np.timedelta64(1, "D")
            expected.append(("heading", k, date, int(days)))
        expected += [("read", date), ("progress", date), ("step",)]

    assert calls == expected
    assert manager._idx == len(TIMELINE_DATES)
