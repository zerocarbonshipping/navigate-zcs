# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The flexibility markets of flexible regulations and the beliefs of their cost."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID, RegulationSchemeID
from navigate.simulation.policy.compliance import calculate_vessel_account
from navigate.util import derive_smoothing_alpha, divide_nonzero, update_belief_path

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


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
        Scope of the bunkering LP: the existing market goes to the profiles, the
        expected one to the expectations.
    idx
        Time-step index of the bunkering LP.
    """
    for regulation in regulations.values():
        is_flexible = regulation.scheme == RegulationSchemeID.FLEXIBLE
        if not (regulation.active and is_flexible):
            continue

        _calculate_flexibility_market(regulation, vessels, multipliers, scope, idx)


def update_regulation_flexibility_beliefs(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Update flexibility cost belief and apply expected expenses for flexible regulations.

    The raw flexibility cost (the cost the market clearing derives from the shadow
    price of the pooled threshold) is smoothed via exponential moving average, in place
    on the regulation expectation's belief array. This prevents small changes in future
    fuel availability from translating into expectations of large flexibility-cost
    differences.

    The expected flexibility expenses of each policed vessel are then applied as the net
    flexibility units (flexibility units minus surplus units, stored by the market
    clearing) valued at the smoothed cost. Surplus revenue is implicitly valued at the
    same smoothed cost through the net units.

    Parameters
    ----------
    regulations
        Mapping of regulation name to regulation object.
    vessels
        Mapping of vessel name to vessel object.
    timeline
        Simulation timeline in days.
    idx
        Current outer time-step index.
    """
    for regulation in regulations.values():
        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        flexibility_horizon = regulation.flexibility_horizon.get()
        alpha = derive_smoothing_alpha(idx, flexibility_horizon, timeline)

        expectation = regulation.expectation
        raw_cost = expectation.get_flexibility_cost()
        belief = expectation.get_belief_flexibility_cost()

        update_belief_path(raw_cost, belief, alpha, idx)

        for vessel_name, vessel in vessels.items():
            if not regulation.vessel_is_policed(vessel_name):
                continue

            net_units = expectation.get_vessel_net_flexibility_units(vessel_name)
            expenses = net_units[idx:] * belief[idx:]
            vessel.expectation.add_flexibility_expenses_path(idx, expenses)


def _calculate_flexibility_market(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    multipliers: dict[str, float],
    scope: BunkerScopeID,
    idx: int,
) -> None:
    """Clear the flexibility market of one regulation; see the public function."""
    expectation = regulation.expectation
    profile = regulation.profile

    total_remedial_units = expectation.get_pooled_remedial_units(idx)
    remedial_cost = expectation.get_remedial_cost(idx)
    total_remedial_expenses = total_remedial_units * remedial_cost

    # per vessel, the units short of (non-compliance) or beyond (surplus) its allowance
    non_compliance_units = {}
    surplus_units = {}
    total_non_compliance_units = 0.0
    total_surplus_units = 0.0
    for vessel_name, multiplier in multipliers.items():
        if not regulation.vessel_is_policed(vessel_name):
            continue

        account = calculate_vessel_account(regulation, vessel_name, idx)
        non_compliance = max(account.emissions - account.allowance, 0.0)
        surplus = max(account.allowance - account.emissions, 0.0)

        non_compliance_units[vessel_name] = non_compliance
        surplus_units[vessel_name] = surplus
        total_non_compliance_units += multiplier * non_compliance
        total_surplus_units += multiplier * surplus

    # the non-compliance not remediated is covered by flexibility units
    total_flexibility_units = total_non_compliance_units - total_remedial_units

    # the fraction of non-compliance remediated through remedial units rather than
    # surplus units, capped at one against the numerical instability of vessels with
    # a low multiplier (the jump-start fraction)
    ratio = divide_nonzero(
        total_remedial_units, total_non_compliance_units, default=1.0
    )
    remedial_fraction = min(1.0, np.float64(ratio))

    flexibility_cost = expectation.get_pooled_shadow_price(idx)

    # the flexibility units and surplus units may be at a disequilibrium if the
    # surplus-generating fuels are so cheap (e.g., due to subsidies) that they are a
    # good business case regardless of the remuneration from selling them, seen as
    # over-compliance with the global regulation target; the scaling requires
    # positive flexibility units, which numerical instability can make negative
    if total_flexibility_units > 0.0 and total_surplus_units > total_flexibility_units:
        # reduce the value of surplus units and the cost of flexibility units
        # linearly, from the threshold down to the zero line, ignoring the option of
        # negative emissions
        cost_scaling = divide_nonzero(total_flexibility_units, total_surplus_units)
        flexibility_cost = flexibility_cost * np.float64(cost_scaling)

    total_flexibility_expenses = total_flexibility_units * flexibility_cost
    total_surplus_revenue = total_surplus_units * flexibility_cost

    if scope == BunkerScopeID.EXISTING:
        profile.add_remedial_units(total_remedial_units, idx)
        profile.add_remedial_expenses(total_remedial_expenses, idx)
        profile.set_flexibility_cost(idx, flexibility_cost)
        profile.set_flexibility_units(idx, total_flexibility_units)
        profile.set_flexibility_expenses(idx, total_flexibility_expenses)
        profile.set_surplus_units(idx, total_surplus_units)
        profile.set_surplus_revenue(idx, total_surplus_revenue)

    else:
        expectation.set_flexibility_cost(idx, flexibility_cost)

    # the flexibility units are distributed by equal fraction to all vessels with
    # non-compliance
    for vessel_name, non_compliance in non_compliance_units.items():
        vessel = vessels[vessel_name]
        surplus = surplus_units[vessel_name]

        remedial_units = non_compliance * remedial_fraction
        flexibility_units = non_compliance * (1.0 - remedial_fraction)
        remedial_expenses = remedial_units * remedial_cost

        if scope == BunkerScopeID.EXISTING:
            flexibility_expenses = flexibility_units * flexibility_cost
            surplus_revenue = surplus * flexibility_cost

            vessel.profile.add_remedial_units(regulation.name, remedial_units, idx)
            vessel.profile.add_remedial_expenses(remedial_expenses, idx)
            vessel.profile.add_flexibility_expenses(flexibility_expenses, idx)
            vessel.profile.add_surplus_revenue(surplus_revenue, idx)

        else:
            vessel.expectation.add_remedial_expenses(idx, remedial_expenses)

            # the expected flexibility expenses and surplus revenue are not applied
            # with the raw flexibility cost: only the net units are stored, and the
            # belief update applies the expenses with the smoothed flexibility cost
            net_units = flexibility_units - surplus
            expectation.set_vessel_net_flexibility_units(idx, vessel_name, net_units)
