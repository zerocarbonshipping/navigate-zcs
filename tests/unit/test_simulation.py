# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the time-stepping loop of SimulationManager."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from navigate import simulation
from navigate.simulation import SimulationManager

# a start date before 1970 with a yearly step landing on 1970-01-01, continuing past it
TIMELINE_DATES = [
    np.datetime64("1969-01-01"),
    np.datetime64("1970-01-01"),
    np.datetime64("1971-01-01"),
    np.datetime64("1972-01-01"),
]


def test_run_simulation_logs_banner_then_reads_events_then_steps(monkeypatch):
    """
    Each date after the first logs its banner before its events are read.

    The dates cross 1970-01-01, and every one of them is still stepped.
    """
    calls = []
    dateline = np.array(TIMELINE_DATES, dtype="datetime64[D]")

    monkeypatch.setattr(
        simulation,
        "log_time_step_breaker",
        lambda logger, idx, date, days: calls.append(("banner", idx, date, days)),
    )

    manager = SimpleNamespace(
        parser=SimpleNamespace(read_events=lambda date: calls.append(("read", date))),
        dateline=dateline,
        _idx=0,
    )
    manager._progress_date_time = lambda date: calls.append(("progress", date))
    manager._perform_time_step = lambda: calls.append(("step",))

    SimulationManager._run_simulation(manager)

    expected = []
    for k, date in enumerate(dateline):
        if k > 0:
            days = (date - dateline[0]) / np.timedelta64(1, "D")
            expected.append(("banner", k, date, days))
        expected += [("read", date), ("progress", date), ("step",)]

    assert calls == expected
    assert manager._idx == len(TIMELINE_DATES)
