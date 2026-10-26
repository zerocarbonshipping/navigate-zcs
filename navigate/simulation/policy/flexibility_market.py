# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The flexibility markets of flexible regulations and the beliefs of their cost."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from navigate.core.enum_ import BunkerScopeID, RegulationSchemeID
from navigate.simulation.policy._policed import (
    calculate_vessel_account,
    select_policed,
)
from navigate.util import derive_smoothing_alpha, divide_nonzero, update_belief_path

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


class _Units(NamedTuple):
    """Remedial, flexibility and surplus units of a regulation or one of its vessels."""

    remedial: float
    flexibility: float
    surplus: float


class _Market(NamedTuple):
    """A regulation's flexibility market cleared at one time step."""

    remedial_cost: float
    flexibility_cost: float
    total: _Units
    vessels: dict[str, _Units]


def calculate_flexibility_markets(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    multipliers: dict[str, float],
    scope: BunkerScopeID,
    idx: int,
) -> None:
    """
    Clear the flexibility market of each active FLEXIBLE regulation from the LP results.

    The non-compliance the remedial units leave uncovered is met with flexibility units
    bought from the vessels beyond their allowance, at the shadow price of the pooled
    threshold, scaled down when the surplus exceeds the demand; a heuristic allocates
    the units and their cost between the vessels.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    multipliers
        Multiplier of each vessel in the bunkering LP, in the LP's order, which the
        sums over the vessels follow.
    scope
        Scope of the bunkering LP: the existing market goes to the results, the
        expected one to the expectations.
    idx
        Time-step index of the bunkering LP.
    """
    for regulation in regulations.values():
        is_flexible = regulation.scheme == RegulationSchemeID.FLEXIBLE
        if not (regulation.active and is_flexible):
            continue

        market = _clear_flexibility_market(regulation, multipliers, idx)

        if scope == BunkerScopeID.EXISTING:
            _record_market(regulation, vessels, market, idx)
        else:
            _calculate_market_expectations(regulation, vessels, market, idx)


def update_regulation_flexibility_beliefs(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Smooth each FLEXIBLE regulation's flexibility cost and apply its vessels' expenses.

    The raw flexibility cost the market clearing derived from the shadow price is
    smoothed by an exponential moving average, in place on the expectation's belief, so
    that small changes in future fuel availability do not become expectations of large
    differences in flexibility cost.

    A policed vessel's expected flexibility expenses are its net flexibility units,
    flexibility minus surplus units, valued at the smoothed cost, which values its
    surplus revenue at that cost too.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    for regulation in regulations.values():
        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        expectation = regulation.expectation
        horizon = regulation.flexibility_horizon.get()

        alpha = derive_smoothing_alpha(idx, horizon, timeline)
        raw_cost = expectation.get_flexibility_cost()
        belief = expectation.get_belief_flexibility_cost()
        update_belief_path(raw_cost, belief, alpha, idx)

        for vessel_name, vessel in select_policed(regulation, vessels).items():
            net_units = expectation.get_vessel_net_flexibility_units(vessel_name)
            expenses = net_units[idx:] * belief[idx:]
            vessel.expectation.add_flexibility_expenses(idx, expenses)


def _clear_flexibility_market(
    regulation: Regulation, multipliers: dict[str, float], idx: int
) -> _Market:
    """Clear the flexibility market of one regulation; see the public function."""
    expectation = regulation.expectation
    total_remedial = expectation.get_pooled_remedial_units(idx)
    remedial_cost = expectation.get_remedial_cost(idx)
    shadow_price = expectation.get_pooled_shadow_price(idx)

    # per vessel, the units short of (non-compliance) or beyond (surplus) its allowance
    balances: dict[str, tuple[float, float]] = {}
    total_non_compliance = 0.0
    total_surplus = 0.0
    for vessel_name, multiplier in select_policed(regulation, multipliers).items():
        account = calculate_vessel_account(regulation, vessel_name, idx)
        non_compliance = max(account.emissions - account.allowance, 0.0)
        surplus = max(account.allowance - account.emissions, 0.0)

        balances[vessel_name] = (non_compliance, surplus)
        total_non_compliance += multiplier * non_compliance
        total_surplus += multiplier * surplus

    # the non-compliance not remediated is covered by flexibility units
    total_flexibility = total_non_compliance - total_remedial

    # the share of the non-compliance remediated rather than covered by flexibility
    # units, capped at one against the numerical instability of vessels with a low
    # multiplier (the jump-start fraction)
    ratio = divide_nonzero(total_remedial, total_non_compliance, default=1.0)
    remedial_fraction = min(1.0, np.float64(ratio))

    # the surplus may exceed the flexibility units when the surplus-generating fuels
    # pay off without the remuneration (e.g., through subsidies), an over-compliance
    # with the global target; numerical instability can make the flexibility units
    # negative, which the scaling excludes
    if total_surplus > total_flexibility > 0.0:
        # the cost falls linearly from the threshold to the zero line, ignoring
        # negative emissions
        cost_scaling = divide_nonzero(total_flexibility, total_surplus)
        flexibility_cost = shadow_price * np.float64(cost_scaling)
    else:
        flexibility_cost = shadow_price

    # every vessel's non-compliance splits into remedial and flexibility units by the
    # same fraction
    vessel_units: dict[str, _Units] = {}
    for vessel_name, (non_compliance, surplus) in balances.items():
        remedial = non_compliance * remedial_fraction
        flexibility = non_compliance * (1.0 - remedial_fraction)
        vessel_units[vessel_name] = _Units(remedial, flexibility, surplus)

    total = _Units(total_remedial, total_flexibility, total_surplus)
    return _Market(remedial_cost, flexibility_cost, total, vessel_units)


def _record_market(
    regulation: Regulation, vessels: dict[str, Vessel], market: _Market, idx: int
) -> None:
    """Write a cleared flexibility market to the results."""
    results = regulation.results
    total = market.total
    remedial_cost = market.remedial_cost
    flexibility_cost = market.flexibility_cost

    remedial_expenses = total.remedial * remedial_cost
    flexibility_expenses = total.flexibility * flexibility_cost
    surplus_revenue = total.surplus * flexibility_cost

    results.remedial_units[idx] += total.remedial
    results.remedial_expenses[idx] += remedial_expenses
    results.flexibility_cost[idx] = flexibility_cost
    results.flexibility_units[idx] = total.flexibility
    results.flexibility_expenses[idx] = flexibility_expenses
    results.surplus_units[idx] = total.surplus
    results.surplus_revenue[idx] = surplus_revenue

    for vessel_name, units in market.vessels.items():
        vessel = vessels[vessel_name]

        remedial_expenses = units.remedial * remedial_cost
        flexibility_expenses = units.flexibility * flexibility_cost
        surplus_revenue = units.surplus * flexibility_cost

        vessel.results.remedial_units[regulation.name][idx] += units.remedial
        vessel.results.remedial_expenses[idx] += remedial_expenses
        vessel.results.flexibility_expenses[idx] += flexibility_expenses
        vessel.results.surplus_revenue[idx] += surplus_revenue


def _calculate_market_expectations(
    regulation: Regulation, vessels: dict[str, Vessel], market: _Market, idx: int
) -> None:
    """Write a cleared flexibility market to the expectations."""
    expectation = regulation.expectation
    expectation.set_flexibility_cost(idx, market.flexibility_cost)

    # the flexibility expenses and surplus revenue wait for the belief update, which
    # values the net flexibility units at the smoothed rather than the raw cost
    for vessel_name, units in market.vessels.items():
        vessel = vessels[vessel_name]

        remedial_expenses = units.remedial * market.remedial_cost
        net_units = units.flexibility - units.surplus

        vessel.expectation.add_remedial_expenses(idx, remedial_expenses)
        expectation.set_vessel_net_flexibility_units(idx, vessel_name, net_units)
