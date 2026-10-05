# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests for the time-stepping loop of SimulationManager."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from helpers.simulation import check_invariants, run_simulation
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


# the transfer drops LP values below the solution tolerance, so a fuel the
# optimum never bunkers carries a demand of exactly zero; the bound only keeps
# the assertion from hinging on that cutoff
EPS_UNUSED_FUEL_SHARE = 1e-9

PORT_EVENT_DECK = Path(__file__).resolve().parent / "simulations" / "port_event_timing"
EVENT_DATE = np.datetime64("2028-01-01")


@pytest.fixture(scope="module")
def port_event_manager():
    return run_simulation(PORT_EVENT_DECK)


def _fuel_shares(manager: SimulationManager, idx: int) -> dict[str, float]:
    """Share of each fuel in the fleet's expected bunkering at one step."""
    fleet = manager.nodes.fleets["container_15000_teu"]
    demand = {f: float(d[idx]) for f, d in fleet.expectation.get_fuel_demand().items()}
    total = sum(demand.values())

    assert total > 0.0, f"No expected bunkering at {manager.dateline[idx]}"
    return {f: d / total for f, d in demand.items()}


def test_port_event_reaches_expected_bunkering_of_its_own_step(port_event_manager):
    """
    A port event dated at a step sets the prices that step's expected bunkering sees.

    The deck offers two oil fuels identical but for price: oil_cheap at 500 and
    oil_dear at 600 USD/ton. An event at 2028 adds a 1000 USD/ton handling cost
    to oil_cheap, so from 2028 on it costs 1500 against 600. With no policy and
    no bunkering inertia the cost-minimizing bunkering takes only the cheaper
    fuel: oil_cheap at 2027, oil_dear at 2028. Each step's expected bunkering
    writes the fleet fuel demand from its own index on, so after the run the
    value at an index is that step's own expectation for itself.
    """
    manager = port_event_manager
    check_invariants(manager)

    event_idx = int(np.flatnonzero(manager.dateline == EVENT_DATE)[0])
    before = _fuel_shares(manager, event_idx - 1)
    at_event = _fuel_shares(manager, event_idx)

    # guard: before the event the price spread alone decides the fuel
    assert before["oil_dear"] <= EPS_UNUSED_FUEL_SHARE, (
        f"oil_dear bunkered before the event: {before}"
    )
    assert at_event["oil_cheap"] <= EPS_UNUSED_FUEL_SHARE, (
        "Expected bunkering at the event step still bunkers oil_cheap at its "
        f"pre-event price: {at_event}"
    )
