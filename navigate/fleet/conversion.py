# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Fuel conversion of existing vessels from one vessel type to another.

The evaluation runs in three phases per fleet and time-step:

1. ``propose_fuel_conversions`` computes the proposed conversion counts and changes no
   fleet state.
2. ``reconcile_fuel_conversion_caps`` scales the proposals to the per-pair flow caps.
3. ``apply_fuel_conversions`` updates the fleet: multipliers, profile and expenses.

The phases communicate through one ``_ConversionProposal`` per (from-type, increment)
cohort, each holding a ``_ConversionCandidate`` per destination type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID, UtilityID
from navigate.core.increment import VesselIncrement
from navigate.economics.decision import calculate_asset_shares
from navigate.economics.flows import expand_to_flow, trim_flow_to_lifetime
from navigate.economics.metric import calculate_net_present_value
from navigate.util import ROUND_OFF, YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray


@dataclass
class _ConversionCandidate:
    """
    One destination vessel type evaluated for conversion out of an increment.

    Parameters
    ----------
    metric
        Net present value of converting one vessel, USD.
    limit
        Supply-capped share limit passed to the DCM, fraction.
    energy_per_vessel
        Energy demand of one vessel of the destination type, GJ/year.
    charge
        Levelized conversion cost per converted vessel, USD/year.
    window
        Levelization window, the destination type's remaining lifetime, years.
    count
        Proposed conversions, number of vessels; set by the DCM and scaled by the
        reconciliation.
    """

    metric: float
    limit: float
    energy_per_vessel: float
    charge: float
    window: float
    count: float = 0.0


@dataclass
class _ConversionProposal:
    """
    Proposed conversions out of one (from-type, increment) cohort.

    Parameters
    ----------
    name_from
        Name of the source vessel type.
    increment_idx
        Index of the cohort in the source type's increment list.
    age
        Age of the cohort, years.
    age_span
        Age-bin width of the cohort, years.
    candidates
        Evaluated candidates, keyed by destination vessel-type name.
    """

    name_from: str
    increment_idx: int
    age: float
    age_span: float
    candidates: dict[str, _ConversionCandidate]


@dataclass
class _ConversionSource:
    """
    Per-source-vessel-type invariants of one propose pass.

    Parameters
    ----------
    name
        Name of the source vessel type.
    fuel_type
        Primary fuel type of the source vessel type.
    energy_per_vessel
        Energy demand of one source vessel, GJ/year.
    fuel_cost_flow
        Expected yearly fuel cost flow of one source vessel, USD/year.
    capex_npv
        Summed ship CAPEX NPV, USD; it non-dimensionalizes the conversion NPV in the
        DCM.
    conversion_costs
        Cost of converting one vessel, keyed by destination vessel-type name.
    """

    name: str
    fuel_type: FuelTypeID
    energy_per_vessel: float
    fuel_cost_flow: FloatArray
    capex_npv: float
    conversion_costs: dict[str, ForecastInput]


def perform_fuel_conversions(
    fleet: Fleet, idx: int, timeline: FloatArray, time_step: float
) -> None:
    """
    Convert existing vessels to another vessel type where the business case holds.

    Runs the three phases described in the module docstring. The difference in future
    maintenance cost is disregarded, as it is negligible next to the conversion cost
    and the difference in fuel cost.

    Parameters
    ----------
    fleet
        Fleet whose vessels may convert.
    idx
        Current time-step index.
    timeline
        Simulation timeline, days.
    time_step
        Current time-step size, days.
    """
    if not fleet.can_fuel_convert():
        return

    # counted before the newbuilds, which are inserted later in the same time-step
    existing_total = sum(fleet.get_multipliers())

    proposals = propose_fuel_conversions(fleet, idx, time_step)
    if not proposals:
        return

    reconcile_fuel_conversion_caps(fleet, proposals, time_step, existing_total)
    apply_fuel_conversions(fleet, proposals, idx, timeline)


def propose_fuel_conversions(
    fleet: Fleet, idx: int, time_step: float
) -> list[_ConversionProposal]:
    """
    Walk the (from-type, eligible-increment, to-type) nest to produce conversion counts.

    Changes no fleet state. A working copy of the fuel-type supply excess is debited
    as proposals are gathered, so the DCM's supply cap on each target fuel holds across
    increments. The per-pair flow caps are applied later, by
    ``reconcile_fuel_conversion_caps``.

    The supply excess is debited with the uncapped DCM share, is not refunded when the
    reconciliation scales a pair down, and the proposals are not re-run. An early pair
    that proposes more than its cap permits can therefore use up a target fuel's
    supply, leaving later pairs unproposed and some of that supply unused, and the
    conversion mix depends on the walk order whenever caps bind on a shared target
    fuel. Fuel conversion is a single forward pass per time-step, like the rest of the
    long-term decision logic: the DCM answers whether the vessels want to convert given
    the expected supply, and the per-pair cap is a hard ceiling on that completed
    choice.

    Parameters
    ----------
    fleet
        Fleet whose vessels may convert.
    idx
        Current time-step index of the energy and cost-flow lookups.
    time_step
        Current time-step size, days.

    Returns
    -------
    list[_ConversionProposal]
        One proposal per (from-type, increment) pair with a viable business case, in
        walk order.
    """
    retrofit_frequency = fleet.retrofit_frequency.get()
    minimum_age = fleet.fuel_conversion_minimum_age.get()
    time_step_years = time_step / YEAR

    vessels = {vessel.name: vessel for vessel in fleet.vessels}

    # a working copy of the previous step's totals, which the profile phase writes
    # after this runs; the proposals debit it so the DCM supply cap stays realistic
    supply_excess = {
        fuel_type: fleet.expectation.get_fuel_type_supply(fuel_type)
        - fleet.expectation.get_fuel_type_demand(fuel_type)
        for fuel_type in FuelTypeID
    }

    proposals = []

    for v, vessel_from in enumerate(fleet.vessels):
        source = _extract_conversion_source(fleet, vessel_from, idx)
        if source is None:
            continue

        # increments are walked youngest to oldest (index 0 is the oldest cohort); when
        # target-fuel supply binds, younger cohorts with longer remaining lifetimes
        # claim the working supply_excess first
        increments = fleet.increments[v]
        for increment_idx in reversed(range(len(increments))):
            increment = increments[increment_idx]

            if not is_retrofit_cycle(
                increment.age, retrofit_frequency, time_step_years
            ):
                continue

            avg_age = round(increment.age + increment.age_span / 2.0, ROUND_OFF)
            if avg_age < minimum_age:
                continue

            remaining_lifetime_from = round(
                vessel_from.lifetime.get() - avg_age, ROUND_OFF
            )
            if remaining_lifetime_from <= 0.0:
                continue

            multiplier = increment.multiplier
            if multiplier <= 0:
                continue

            candidates = _evaluate_increment(
                fleet,
                vessels,
                source,
                avg_age,
                remaining_lifetime_from,
                multiplier,
                supply_excess,
                idx,
            )
            if not candidates:
                continue

            proposals.append(
                _ConversionProposal(
                    source.name,
                    increment_idx,
                    increment.age,
                    increment.age_span,
                    candidates,
                )
            )

            # update working supply_excess so subsequent increments / from-types see the
            # encumbrance
            for name_to, candidate in candidates.items():
                if not candidate.count:
                    continue

                supply_excess[source.fuel_type] += (
                    candidate.count * source.energy_per_vessel
                )
                supply_excess[vessels[name_to].primary_fuel_type] -= (
                    candidate.count * candidate.energy_per_vessel
                )

    return proposals


def reconcile_fuel_conversion_caps(
    fleet: Fleet,
    proposals: list[_ConversionProposal],
    time_step: float,
    existing_total: float,
) -> None:
    """
    Scale the proposals in place to the per-pair flow caps.

    ``set_fuel_conversion_limit("from", "to", l)`` caps the fraction of the total fleet
    allowed to convert on a (from, to) lane per year:
    ``pair_cap[from, to] = l * time_step / YEAR * existing_total``. The cap acts on the
    pair's summed conversion count; a pair above its cap has every increment scaled to
    fit.

    Parameters
    ----------
    fleet
        Fleet holding the conversion limits.
    proposals
        Output of ``propose_fuel_conversions``; its counts are rescaled in place.
    time_step
        Current time-step size, days.
    existing_total
        Number of vessels in the fleet before newbuilds.
    """
    if existing_total <= 0.0:
        return

    pair_proposed: dict[tuple[str, str], float] = {}
    for proposal in proposals:
        for name_to, candidate in proposal.candidates.items():
            pair = (proposal.name_from, name_to)
            pair_proposed[pair] = pair_proposed.get(pair, 0.0) + candidate.count

    cap_scale = time_step / YEAR * existing_total

    pair_scale = {}
    for pair, proposed in pair_proposed.items():
        if proposed <= 0.0:
            continue

        pair_cap = fleet.fuel_conversion_limit[pair].get() * cap_scale
        if proposed > pair_cap:
            pair_scale[pair] = pair_cap / proposed

    if pair_scale:
        for proposal in proposals:
            for name_to, candidate in proposal.candidates.items():
                scale = pair_scale.get((proposal.name_from, name_to))
                if scale is not None:
                    candidate.count *= scale


def apply_fuel_conversions(
    fleet: Fleet, proposals: list[_ConversionProposal], idx: int, timeline: FloatArray
) -> None:
    """
    Apply the reconciled conversion counts to the fleet.

    Every source-side decrement runs before any destination-side insert, so no vessel
    converts twice within one time-step.

    Parameters
    ----------
    fleet
        Fleet whose vessels convert.
    proposals
        Output of ``propose_fuel_conversions`` after ``reconcile_fuel_conversion_caps``;
        read only.
    idx
        Current time-step index, where the profile is written and the expenses start.
    timeline
        Simulation timeline, days.
    """
    indices = {vessel.name: i for i, vessel in enumerate(fleet.vessels)}

    _apply_from_side(fleet, proposals, indices, idx, timeline)
    _apply_to_side(fleet, proposals, indices)


def is_retrofit_cycle(
    age: float, retrofit_frequency: float, time_step: float, decimals: int = 2
) -> bool:
    """
    Return whether an increment is at a retrofit cycle.

    It is when its age lies within one time-step past a multiple of the retrofit
    frequency, and it is older than one time-step.

    Parameters
    ----------
    age
        Age of the increment, years.
    retrofit_frequency
        Interval between retrofit opportunities, years.
    time_step
        Time-step size, years.
    decimals
        Decimals the age and time-step are rounded to before comparison.

    Returns
    -------
    bool
        Whether the increment is at a retrofit cycle.
    """
    age_ = round(age, decimals)
    time_step_ = round(time_step, decimals)
    return (age_ > time_step_) and ((age_ % retrofit_frequency) < time_step_)


def _extract_conversion_source(
    fleet: Fleet, vessel_from: Vessel, idx: int
) -> _ConversionSource | None:
    """
    Bundle the per-source-vessel-type invariants of a propose pass.

    Parameters
    ----------
    fleet
        Fleet holding the conversion costs.
    vessel_from
        Source vessel type.
    idx
        Current time-step index of the expectation lookups.

    Returns
    -------
    _ConversionSource | None
        The source bundle, or None when no conversion lane starts at the vessel type.
    """
    conversion_costs = {
        name_to: cost
        for (name_from, name_to), cost in fleet.fuel_conversion_cost.items()
        if name_from == vessel_from.name and cost is not None
    }

    if not conversion_costs:
        return None

    return _ConversionSource(
        vessel_from.name,
        vessel_from.primary_fuel_type,
        float(vessel_from.expectation.get_total_energy(idx)),
        vessel_from.expectation.get_fuel_cost_flow(),
        vessel_from.expectation.get_capex_npv(idx),
        conversion_costs,
    )


def _evaluate_increment(
    fleet: Fleet,
    vessels: dict[str, Vessel],
    source: _ConversionSource,
    avg_age: float,
    remaining_lifetime_from: float,
    multiplier: float,
    supply_excess: dict[FuelTypeID, float],
    idx: int,
) -> dict[str, _ConversionCandidate]:
    """
    Evaluate every destination type for one eligible increment and run the DCM on it.

    Parameters
    ----------
    fleet
        Fleet holding the conversion settings.
    vessels
        Vessel lookup by name.
    source
        Invariants of the source vessel type.
    avg_age
        Average age of the increment, years.
    remaining_lifetime_from
        Remaining lifetime of the source type at the increment's average age, years.
    multiplier
        Number of vessels in the increment.
    supply_excess
        Working supply excess per fuel type, GJ/year; read only.
    idx
        Current time-step index.

    Returns
    -------
    dict[str, _ConversionCandidate]
        Candidates keyed by destination name, with the DCM's conversion counts; empty,
        without running the DCM, when no destination qualifies.
    """
    candidates = {}

    for name_to, conversion_cost in source.conversion_costs.items():
        if (not fleet.allow_vessel[name_to]) or (
            not fleet.conversion_available[name_to]
        ):
            continue

        vessel_to = vessels[name_to]
        candidate = _evaluate_candidate(
            vessel_to,
            conversion_cost,
            source,
            avg_age,
            remaining_lifetime_from,
            multiplier,
            supply_excess[vessel_to.primary_fuel_type],
            idx,
        )
        if candidate is not None:
            candidates[name_to] = candidate

    if not candidates:
        return candidates

    # the BAU sentinel (metric=0., limit=1.) sits at index -1 of the DCM input and is
    # dropped on return
    metrics = [candidate.metric for candidate in candidates.values()] + [0.0]
    limits = [candidate.limit for candidate in candidates.values()] + [1.0]

    uptakes, _ = calculate_asset_shares(
        metrics,
        UtilityID.SIGNED_REFERENCE,
        fleet.fuel_conversion_sensitivity.get(),
        reference=source.capex_npv,
        limits=limits,
    )

    # store as conversion counts so reconciliation can scale per-pair without a
    # re-multiply; strict=False drops the BAU sentinel's share
    for candidate, share in zip(candidates.values(), uptakes, strict=False):
        candidate.count = share * multiplier

    return candidates


def _evaluate_candidate(
    vessel_to: Vessel,
    conversion_cost: ForecastInput,
    source: _ConversionSource,
    avg_age: float,
    remaining_lifetime_from: float,
    multiplier: float,
    supply: float,
    idx: int,
) -> _ConversionCandidate | None:
    """
    Evaluate the business case of converting increment vessels to one destination type.

    Parameters
    ----------
    vessel_to
        Destination vessel type.
    conversion_cost
        Lump-sum cost of converting one vessel to the destination type, USD.
    source
        Invariants of the source vessel type.
    avg_age
        Average age of the increment, years.
    remaining_lifetime_from
        Remaining lifetime of the source type at the increment's average age, years.
    multiplier
        Number of vessels in the increment.
    supply
        Working supply excess of the destination type's fuel, GJ/year.
    idx
        Current time-step index.

    Returns
    -------
    _ConversionCandidate | None
        The evaluated candidate with ``count`` left at zero, or None when the
        destination type has no remaining lifetime or no fuel supply excess.
    """
    remaining_lifetime_to = round(vessel_to.lifetime.get() - avg_age, ROUND_OFF)
    if remaining_lifetime_to <= 0.0:
        return None

    if supply <= 0.0:
        return None

    discount_rate = vessel_to.cost_of_capital.get()
    # a numpy scalar keeps numpy division: a zero energy gives an unbounded
    # vessel count, not a ZeroDivisionError
    energy_per_vessel = np.float64(vessel_to.expectation.get_total_energy(idx))
    maximum_vessels = supply / energy_per_vessel
    limit = min(maximum_vessels / multiplier, 1.0)

    cost_fuel_to = vessel_to.expectation.get_fuel_cost_flow()

    # fuel savings count over the window both the current and the converted
    # vessel type still serve; the conversion cost is a lump sum up front
    common_window = min(remaining_lifetime_from, remaining_lifetime_to)
    cash_flow = trim_flow_to_lifetime(
        source.fuel_cost_flow, common_window
    ) - trim_flow_to_lifetime(cost_fuel_to, common_window)
    cash_flow[0] -= conversion_cost.get()

    metric = calculate_net_present_value(cash_flow, discount_rate)

    # for expense reporting the cost is levelized exactly: a constant yearly
    # charge whose NPV over the destination type's remaining lifetime equals
    # the conversion cost
    ones_flow = expand_to_flow(remaining_lifetime_to, 1.0)
    charge = conversion_cost.get() / calculate_net_present_value(
        ones_flow, discount_rate
    )

    return _ConversionCandidate(
        metric, limit, energy_per_vessel, charge, remaining_lifetime_to
    )


def _apply_from_side(
    fleet: Fleet,
    proposals: list[_ConversionProposal],
    indices: dict[str, int],
    idx: int,
    timeline: FloatArray,
) -> None:
    """
    Decrement source-side multipliers, write the profile, and book transition expenses.

    Parameters
    ----------
    fleet
        Fleet whose vessels convert.
    proposals
        Reconciled proposals.
    indices
        Vessel index lookup by name.
    idx
        Current time-step index.
    timeline
        Simulation timeline, days.
    """
    years_ahead = timeline[idx:] / YEAR
    expenses_ahead = fleet.fuel_conversion_expenses[idx:]

    for proposal in proposals:
        increments_from = fleet.increments[indices[proposal.name_from]]

        for name_to, candidate in proposal.candidates.items():
            if not candidate.count:
                continue

            increments_from[proposal.increment_idx].multiplier -= candidate.count

            if proposal.increment_idx == 0 and increments_from[0].baseline is not None:
                increments_from[0].baseline -= candidate.count

            fleet.profile.add_fuel_conversions(
                proposal.name_from, name_to, candidate.count, idx
            )

            _book_conversion_expenses(expenses_ahead, years_ahead, candidate)


def _book_conversion_expenses(
    expenses_ahead: FloatArray, years_ahead: FloatArray, candidate: _ConversionCandidate
) -> None:
    """
    Book the levelized charge over the service window.

    The coverage prorates the final partial year so the booked amounts match
    the levelization identity.

    Parameters
    ----------
    expenses_ahead
        View of the fleet's fuel-conversion expenses from the conversion step onward;
        updated in place.
    years_ahead
        Timeline in years from the conversion step onward.
    candidate
        Conversion providing count, charge, and window.
    """
    coverage = np.clip(
        candidate.window - np.floor(years_ahead - years_ahead[0]), 0.0, 1.0
    )
    expenses_ahead += candidate.count * candidate.charge * coverage


def _apply_to_side(
    fleet: Fleet, proposals: list[_ConversionProposal], indices: dict[str, int]
) -> None:
    """
    Insert converted vessels on the destination side.

    Runs after every source-side decrement so a vessel converted in this timestep cannot
    be converted again within it.

    Parameters
    ----------
    fleet
        Fleet whose vessels convert.
    proposals
        Reconciled proposals.
    indices
        Vessel index lookup by name.
    """
    for proposal in proposals:
        v_from = indices[proposal.name_from]

        for name_to, candidate in proposal.candidates.items():
            if not candidate.count:
                continue

            # resolve the source increment per insert: earlier inserts may have shifted
            # its list
            increment_from = fleet.increments[v_from][proposal.increment_idx]
            _insert_converted_increment(
                fleet.increments[indices[name_to]],
                increment_from,
                candidate.count,
                proposal.age,
                proposal.age_span,
            )


def _insert_converted_increment(
    increments_to: list[VesselIncrement],
    increment_from: VesselIncrement,
    count: float,
    age: float,
    dt: float,
) -> None:
    """
    Insert a converted increment into the destination's age-sorted increment list.

    Parameters
    ----------
    increments_to
        Destination increment list, sorted oldest first; mutated in place.
    increment_from
        Source increment providing the technology package and charter rate carried
        along.
    count
        Number of vessels converted.
    age
        Age of the converted increment, years.
    dt
        Age-bin width of the converted increment, years.
    """
    if increments_to:
        ages_to = np.array([increment.age for increment in increments_to])
        idx_to = int(np.searchsorted(-ages_to, -age, side="right"))
    else:
        idx_to = 0

    # the carried technology charter rate rides along unchanged; the amortization window
    # and discount rate stay those of the source vessel type, a simplification of the
    # same order as disregarding the maintenance cost difference (see
    # perform_fuel_conversions)
    increments_to.insert(
        idx_to,
        VesselIncrement(
            count,
            age,
            dt,
            package_uptake=increment_from.package_uptake.copy(),
            technology_charter_rate=increment_from.technology_charter_rate,
        ),
    )

    # only the oldest cohort holds the baseline, so a new oldest cohort takes it over
    if idx_to == 0:
        if len(increments_to) > 1 and increments_to[1].baseline is not None:
            increments_to[0].baseline = increments_to[1].baseline + count
            increments_to[1].baseline = None
        else:
            increments_to[0].baseline = count
