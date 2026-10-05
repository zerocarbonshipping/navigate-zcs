# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the time-stepping loop of SimulationManager."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from navigate.simulation import SimulationManager

# a start date before 1970 with a yearly step landing on 1970-01-01, continuing past it
TIMELINE_DATES = [
    np.datetime64("1969-01-01"),
    np.datetime64("1970-01-01"),
    np.datetime64("1971-01-01"),
    np.datetime64("1972-01-01"),
]


def test_run_simulation_steps_through_every_date_including_the_epoch():
    """``_run_simulation`` must process 1970-01-01 and every date after it."""
    remaining_dates = iter([*TIMELINE_DATES, None])
    parser = SimpleNamespace(progress_timeline=lambda: next(remaining_dates))

    progressed_dates = []
    stepped_dates = []

    manager = SimpleNamespace(parser=parser, _idx=0, _date=None)

    def _progress_date_time(date):
        progressed_dates.append(date)
        manager._date = date

    def _perform_time_step():
        stepped_dates.append(manager._date)

    manager._progress_date_time = _progress_date_time
    manager._perform_time_step = _perform_time_step

    SimulationManager._run_simulation(manager)

    assert progressed_dates == TIMELINE_DATES
    assert stepped_dates == TIMELINE_DATES
    assert manager._idx == len(TIMELINE_DATES)
