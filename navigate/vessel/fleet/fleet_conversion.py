# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import numpy as np

from navigate.asset import Increment
from navigate.core.enum_ import FuelTypeID, UtilityID
from navigate.core.misc import ROUND_OFF, YEAR
from navigate.investment.decision import calculate_asset_shares
from navigate.investment.flows import as_equal_installments, get_remaining_cost_flow
from navigate.investment.metric import calculate_annualization_factor, calculate_net_present_value
from navigate.util import extract_from_tuple_dict
from navigate.vessel.fleet.fleet_utils import is_retrofit_cycle

if TYPE_CHECKING:
    from navigate.vessel.fleet import Fleet


def perform_fuel_conversions(fleet: Fleet, idx: int, timeline: np.ndarray, time_step: float):
    """
    Evaluate the business case of performing a fuel conversion from one vessel type to another.

    The work is split into three phases:
        1. propose_fuel_conversions   — pure: computes proposed conversion counts per (from, increment, to).
        2. reconcile_fuel_conversion_caps — scales proposals against the per-pair flow caps.
        3. apply_fuel_conversions     — mutates state (multipliers, profile, expenses).

    Notice that we do not account for the cost difference in future maintenance costs of the asset.
    This is considered negligible compared to the cost of the conversion and difference in fuel costs and
    therefore disregarded for simplicity.

    Parameters
    ----------
    fleet
        The fleet instance to perform fuel conversions on.
    idx
        Current time-step index.
    timeline
        Simulation timeline.
    time_step
        Current time-step size.
    """

    if not fleet.can_fuel_convert():
        return

    # must be pre-newbuild: newbuilds are inserted later in the same timestep.
    existing_total = sum(fleet.get_multipliers())

    proposals = propose_fuel_conversions(fleet, idx, time_step)
    if not proposals:
        return

    reconcile_fuel_conversion_caps(fleet, proposals, time_step, existing_total)
    apply_fuel_conversions(fleet, proposals, idx, timeline)


def propose_fuel_conversions(fleet: Fleet, idx: int, time_step: float) -> dict:
    """
    Walk the (from-type, eligible-increment, to-type) nest and produce proposed conversion counts.

    Pure with respect to ``fleet`` (no state mutation). The local ``supply_excess`` working copy
    is updated as proposals are gathered so the DCM's per-target supply cap remains realistic
    across increments. The per-pair flow caps are NOT applied here — they are enforced in
    ``reconcile_fuel_conversion_caps``.

    Model choice — pre-cap supply debit and order dependence
    --------------------------------------------------------
    ``supply_excess`` is debited at proposal time using the *uncapped* DCM share times the
    increment count. ``reconcile_fuel_conversion_caps`` may later scale a pair's conversions
    down to fit a binding per-pair flow cap, but the supply already encumbered in the working
    ``supply_excess`` is not refunded, and proposals are not re-run after reconciliation. Two
    consequences flow from this:

    * If an early (from-type, increment) pair proposes more conversions than its pair cap will
      ultimately permit, it can fully consume the working target-fuel supply and prevent later
      eligible pairs from being proposed at all. After reconciliation scales the early pair down,
      some target-fuel supply remains unused that a fixed-point would have routed elsewhere.
    * Because the walk iterates ``fleet.assets`` and increments in order, the realised conversion
      mix depends on that iteration order whenever caps bind on a shared target fuel.

    This is intentional. Navigate models fuel conversion as a single forward pass per timestep,
    consistent with the rest of the long-term decision logic, which has no inner fixed-point
    loops. The DCM in this stage answers "given expected supply, do these vessels want to
    convert?", and the per-pair flow cap is a hard ceiling layered on top of an already-completed
    choice — not a constraint inside the choice.

    Parameters
    ----------
    fleet
        The fleet instance.
    idx
        Current time-step index. Drives the supply/demand snapshot taken from the previous step
        and the energy/cost-flow lookups on each vessel's expectation.
    time_step
        Current time-step size in dateline units; converted to years to evaluate retrofit cycles.

    Returns
    -------
    Dict keyed by ``(name_from, increment_idx)``. Each entry stores the proposed conversion
    counts for that increment (``'conversions': {name_to: count}``), the increment's ``'age'``
    and ``'dt'``, and the per-vessel cost flows ``'costs_per_vessel'`` used by the apply step.
    """

    retrofit_frequency = fleet.retrofit_frequency.get()
    minimum_age = fleet.fuel_conversion_minimum_age.get()
    time_step_years = time_step / YEAR

    vessels = {vessel.get_name(): vessel for vessel in fleet.assets}

    # working copy — updated as proposals are gathered so the DCM supply cap stays realistic
    # TODO: update to expectation, not profile
    supply_excess = {fuel_type: fleet.profile.get_fuel_type_supply(fuel_type, idx - 1)
                     - fleet.profile.get_fuel_type_demand(fuel_type, idx - 1)
                     for fuel_type in FuelTypeID}

    proposals = {}

    for v, vessel_from in enumerate(fleet.assets):

        name_from = vessel_from.get_name()
        conversion_costs = extract_from_tuple_dict(fleet.fuel_conversion_cost, key1=name_from)
        conversion_costs = {name_to: cost for name_to, cost in conversion_costs.items() if cost is not None}

        if not conversion_costs:
            continue

        cost_fuel_from = deepcopy(vessel_from.expectation.get_fuel_cost_flow())
        energy_from_per_vessel = vessel_from.expectation.get_total_energy(idx)
        fuel_type_from = vessel_from.fuel_type

        # summed ship CAPEX of the vessel being converted, used to non-dimensionalize the conversion NPV
        capex_npv_from = vessel_from.expectation.get_capex_npv(idx)

        # increments are walked oldest → newest (reverse) so the early-out below skips ages that
        # already failed the business case
        increments = fleet.increments[v]
        for i, inc_rev in enumerate(reversed(increments)):

            if not is_retrofit_cycle(inc_rev.age, retrofit_frequency, time_step_years):
                continue

            avg_age = round(inc_rev.age + inc_rev.dt / 2., ROUND_OFF)
            if avg_age < minimum_age:
                continue

            remaining_lifetime_from = vessel_from.lifetime.get() - avg_age
            if remaining_lifetime_from <= 0.:
                continue

            increment_idx = len(increments) - 1 - i
            increment = increments[increment_idx].multiplier
            if increment <= 0:
                continue

            remaining_cost_fuel_from = get_remaining_cost_flow(cost_fuel_from,
                                                               remaining_lifetime_from,
                                                               initial=True)

            metrics, costs, limits, energies_to = {}, {}, {}, {}

            for name_to, conversion_cost in conversion_costs.items():

                vessel_to = vessels[name_to]

                if (not fleet.allow_vessel[name_to]) or (not fleet.conversion_available[name_to]):
                    continue

                remaining_lifetime_to = vessel_to.lifetime.get() - avg_age
                if remaining_lifetime_to <= 0.:
                    continue

                fuel_type_to = vessel_to.fuel_type
                if supply_excess[fuel_type_to] <= 0.:
                    continue

                discount_rate = vessel_to.cost_of_capital.get()
                energy_demand = vessel_to.expectation.get_total_energy(idx)
                maximum_vessels = supply_excess[fuel_type_to] / energy_demand
                limits[name_to] = min(maximum_vessels / increment, 1.)
                energies_to[name_to] = energy_demand

                cost_fuel_to = deepcopy(vessel_to.expectation.get_fuel_cost_flow())
                remaining_cost_fuel_to = get_remaining_cost_flow(cost_fuel_to,
                                                                 remaining_lifetime_to,
                                                                 initial=True)

                length = min(remaining_cost_fuel_from.size, remaining_cost_fuel_to.size)
                delta_cost_flow = remaining_cost_fuel_from[:length] - remaining_cost_fuel_to[:length]

                annualization = calculate_annualization_factor(discount_rate, remaining_lifetime_to)
                conversion_cost_annualized = conversion_cost.get() * remaining_lifetime_to / annualization
                conversion_cost_flow = as_equal_installments(remaining_lifetime_to, conversion_cost_annualized)

                cash_flow = delta_cost_flow
                cash_flow[0] -= conversion_cost.get()

                metrics[name_to] = calculate_net_present_value(cash_flow, discount_rate)
                costs[name_to] = conversion_cost_flow

            if not metrics:
                # no business case at this age implies older increments fail too
                break

            # the BAU sentinel (metric=0., limit=1.) sits at index -1 of the DCM input and is dropped on return
            metrics_list = list(metrics.values()) + [0.]
            limits_list = [limits[name] for name in metrics.keys()] + [1.]

            uptakes_arr, _ = calculate_asset_shares(metrics_list, UtilityID.SIGNED_REFERENCE,
                                                    fleet.fuel_conversion_sensitivity.get(),
                                                    reference=capex_npv_from, limits=limits_list)
            uptakes = {name: share for name, share in zip(metrics.keys(), uptakes_arr)}

            # store as conversion counts so reconciliation can scale per-pair without a re-multiply
            conversions = {name_to: share * increment for name_to, share in uptakes.items()}

            proposals[(name_from, increment_idx)] = {
                'age': inc_rev.age,
                'dt': inc_rev.dt,
                'conversions': conversions,
                'costs_per_vessel': costs,
            }

            # update working supply_excess so subsequent increments / from-types see the encumbrance
            for name_to, count in conversions.items():

                if not count:
                    continue

                supply_excess[fuel_type_from] += count * energy_from_per_vessel
                supply_excess[vessels[name_to].fuel_type] -= count * energies_to[name_to]

    return proposals


def reconcile_fuel_conversion_caps(fleet: Fleet,
                                   proposals: dict,
                                   time_step: float,
                                   existing_total: float) -> None:
    """
    Enforce the per-pair flow cap on the proposals dict, in place.

    ``set_fuel_conversion_limit("from", "to", l)`` caps the fraction of the total fleet allowed to
    convert on a specific (from, to) lane per year:
    ``pair_cap[from, to] = l × time_step / YEAR × existing_total``.

    The cap acts on aggregated conversion counts (not on per-increment shares). If a pair total
    exceeds its cap, every increment of that pair is scaled to fit.

    Parameters
    ----------
    fleet
        The fleet instance.
    proposals
        Output of ``propose_fuel_conversions``. Mutated in place: per-pair conversion counts are
        rescaled when the lane's cap binds.
    time_step
        Current time-step size; used (with ``YEAR``) to convert per-year limits to per-step caps.
    existing_total
        Sum of pre-newbuild fleet multipliers — the denominator for each pair's cap
        (``pair_cap = limit · time_step / YEAR · existing_total``).
    """

    if existing_total <= 0.:
        return

    pair_proposed: dict[tuple[str, str], float] = {}
    for (name_from, _increment_idx), proposal in proposals.items():
        for name_to, count in proposal['conversions'].items():
            pair_proposed[(name_from, name_to)] = pair_proposed.get((name_from, name_to), 0.) + count

    pair_scale: dict[tuple[str, str], float] = {}
    for pair, proposed in pair_proposed.items():

        if proposed <= 0.:
            continue

        pair_cap = fleet.fuel_conversion_limit[pair].get() * time_step / YEAR * existing_total
        if proposed > pair_cap:
            pair_scale[pair] = pair_cap / proposed

    if pair_scale:
        for (name_from, _increment_idx), proposal in proposals.items():
            for name_to in proposal['conversions']:
                scale = pair_scale.get((name_from, name_to))
                if scale is not None:
                    proposal['conversions'][name_to] *= scale


def apply_fuel_conversions(fleet: Fleet, proposals: dict, idx: int, timeline: np.ndarray) -> None:
    """
    Apply finalised conversion counts: decrement from-side multipliers, insert on the to-side, write the
    profile, and accumulate transition expenses. Mirror the ordering of the original implementation —
    from-side decrements happen first across all proposals, then to-side inserts, to avoid multi-stage
    conversions within the same timestep.

    Parameters
    ----------
    fleet
        The fleet instance.
    proposals
        Output of ``propose_fuel_conversions`` after ``reconcile_fuel_conversion_caps`` has rescaled
        it. Read-only here; mutates ``fleet`` instead.
    idx
        Current time-step index, used for profile writes and the expense interpolation start.
    timeline
        Simulation timeline in dateline units; used to compute the years axis for expense
        spreading.
    """

    indices = {vessel.get_name(): i for i, vessel in enumerate(fleet.assets)}
    years = timeline / YEAR

    # from-side decrements + profile + expenses
    for (name_from, increment_idx), proposal in proposals.items():

        v_from = indices[name_from]
        costs = proposal['costs_per_vessel']

        for name_to, conversion in proposal['conversions'].items():

            if not conversion:
                continue

            fleet.increments[v_from][increment_idx].multiplier -= conversion

            # update baseline on oldest increment
            if increment_idx == 0 and fleet.increments[v_from][0].baseline is not None:
                fleet.increments[v_from][0].baseline -= conversion

            fleet.profile.add_fuel_conversions(name_from, name_to, idx, conversion)

            expenses = conversion * costs[name_to]
            fleet.fuel_conversion_expenses[idx:] += np.interp(years[idx:],
                                                              range(idx, idx + expenses.size),
                                                              expenses, left=0., right=0.)

    # to-side inserts (deferred to avoid multi-stage conversions within this timestep)
    for (name_from, increment_idx), proposal in proposals.items():

        v_from = indices[name_from]
        age = proposal['age']
        dt = proposal['dt']

        for name_to, conversion in proposal['conversions'].items():

            if not conversion:
                continue

            v_to = indices[name_to]

            if fleet.increments[v_to]:
                ages_to = np.array([inc.age for inc in fleet.increments[v_to]])
                idx_to = int(np.searchsorted(-ages_to, -age, side='right'))
            else:
                idx_to = 0

            # the carried technology charter rate rides along unchanged; the amortization
            # window and discount rate stay those of the source vessel type — the same
            # simplification level as disregarding the maintenance cost difference above
            increment_from = fleet.increments[v_from][increment_idx]
            pkg = increment_from.package_uptake.copy()
            fleet.increments[v_to].insert(
                idx_to, Increment(conversion, age, dt, package_uptake=pkg,
                                  technology_charter_rate=increment_from.technology_charter_rate))

            # update baseline on oldest increment
            if idx_to == 0:
                if (len(fleet.increments[v_to]) > 1
                        and fleet.increments[v_to][1].baseline is not None):
                    fleet.increments[v_to][0].baseline = fleet.increments[v_to][1].baseline + conversion
                    fleet.increments[v_to][1].baseline = None
                else:
                    fleet.increments[v_to][0].baseline = conversion
