# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Fuel conversion of existing vessels from one vessel type to another.

The evaluation runs in three phases per fleet and time-step:

1. ``propose_fuel_conversions`` — pure: compute proposed conversion counts.
2. ``reconcile_fuel_conversion_caps`` — scale the proposals against the per-pair flow caps.
3. ``apply_fuel_conversions`` — mutate fleet state (multipliers, profile, expenses).

The phases communicate through ``_ConversionProposal`` objects — one per (from-type, increment)
cohort — each holding a ``_ConversionCandidate`` per destination type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID, UtilityID
from navigate.core.increment import Increment
from navigate.economics.decision import calculate_asset_shares
from navigate.economics.flows import expand_to_flow, trim_flow_to_lifetime
from navigate.economics.metric import calculate_net_present_value
from navigate.fleet.utils import is_retrofit_cycle
from navigate.util import ROUND_OFF, YEAR, extract_from_tuple_dict

if TYPE_CHECKING:
    from navigate.core import Scalar
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel


@dataclass
class _ConversionCandidate:
    """One destination vessel type evaluated for conversion out of an increment."""

    metric: float             # net present value of converting one vessel
    limit: float              # supply-capped DCM share limit
    energy_per_vessel: float  # energy demand of one vessel of the destination type
    charge: float             # constant yearly charge per converted vessel (levelized conversion cost)
    window: float             # levelization window: the destination type's remaining lifetime
    count: float = 0.         # proposed conversions; set by the DCM, scaled by reconciliation


@dataclass
class _ConversionProposal:
    """Proposed conversions out of one (from-type, increment) cohort."""

    name_from: str
    increment_idx: int
    age: float
    dt: float
    candidates: dict[str, _ConversionCandidate]  # keyed by destination vessel-type name


@dataclass
class _ConversionSource:
    """Per-source-vessel-type invariants of one propose pass."""

    name: str
    fuel_type: FuelTypeID
    energy_per_vessel: float
    fuel_cost_flow: np.ndarray
    capex_npv: float                     # summed ship CAPEX, non-dimensionalizes the conversion NPV in the DCM
    conversion_costs: dict[str, Scalar]  # keyed by destination vessel-type name


def perform_fuel_conversions(fleet: Fleet, idx: int, timeline: np.ndarray, time_step: float) -> None:
    """
    Evaluate the business case of performing a fuel conversion from one vessel type to another,
    running the three phases described in the module docstring.

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


def propose_fuel_conversions(fleet: Fleet, idx: int, time_step: float) -> list[_ConversionProposal]:
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
    * Because the walk iterates ``fleet.vessels`` and increments in order, the realised conversion
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
    One ``_ConversionProposal`` per (from-type, increment) pair with a viable business case,
    in walk order.
    """

    retrofit_frequency = fleet.retrofit_frequency.get()
    minimum_age = fleet.fuel_conversion_minimum_age.get()
    time_step_years = time_step / YEAR

    vessels = {vessel.name: vessel for vessel in fleet.vessels}

    # working copy — updated as proposals are gathered so the DCM supply cap stays realistic
    # TODO: update to expectation, not profile
    supply_excess = {fuel_type: fleet.profile.get_fuel_type_supply(fuel_type, idx - 1)
                     - fleet.profile.get_fuel_type_demand(fuel_type, idx - 1)
                     for fuel_type in FuelTypeID}

    proposals = []

    for v, vessel_from in enumerate(fleet.vessels):

        source = _extract_conversion_source(fleet, vessel_from, idx)
        if source is None:
            continue

        # increments are walked youngest to oldest (index 0 is the oldest cohort); when
        # target-fuel supply binds, younger cohorts with longer remaining lifetimes claim
        # the working supply_excess first
        increments = fleet.increments[v]
        for increment_idx in reversed(range(len(increments))):

            increment = increments[increment_idx]

            if not is_retrofit_cycle(increment.age, retrofit_frequency, time_step_years):
                continue

            avg_age = round(increment.age + increment.dt / 2., ROUND_OFF)
            if avg_age < minimum_age:
                continue

            remaining_lifetime_from = round(vessel_from.lifetime.get() - avg_age, ROUND_OFF)
            if remaining_lifetime_from <= 0.:
                continue

            multiplier = increment.multiplier
            if multiplier <= 0:
                continue

            candidates = _evaluate_increment(fleet, vessels, source, avg_age,
                                             remaining_lifetime_from, multiplier,
                                             supply_excess, idx)
            if not candidates:
                continue

            proposals.append(_ConversionProposal(source.name, increment_idx,
                                                 increment.age, increment.dt, candidates))

            # update working supply_excess so subsequent increments / from-types see the encumbrance
            for name_to, candidate in candidates.items():

                if not candidate.count:
                    continue

                supply_excess[source.fuel_type] += candidate.count * source.energy_per_vessel
                supply_excess[vessels[name_to].fuel_type] -= candidate.count * candidate.energy_per_vessel

    return proposals


def reconcile_fuel_conversion_caps(fleet: Fleet,
                                   proposals: list[_ConversionProposal],
                                   time_step: float,
                                   existing_total: float) -> None:
    """
    Enforce the per-pair flow cap on the proposals, in place.

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

    pair_proposed = {}
    for proposal in proposals:
        for name_to, candidate in proposal.candidates.items():
            pair = (proposal.name_from, name_to)
            pair_proposed[pair] = pair_proposed.get(pair, 0.) + candidate.count

    cap_scale = time_step / YEAR * existing_total

    pair_scale = {}
    for pair, proposed in pair_proposed.items():

        if proposed <= 0.:
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


def apply_fuel_conversions(fleet: Fleet,
                           proposals: list[_ConversionProposal],
                           idx: int,
                           timeline: np.ndarray) -> None:
    """
    Apply finalised conversion counts: decrement from-side multipliers, insert on the to-side,
    write the profile, and accumulate transition expenses. From-side decrements happen first
    across all proposals, then to-side inserts, to avoid multi-stage conversions within the
    same timestep.

    Parameters
    ----------
    fleet
        The fleet instance.
    proposals
        Output of ``propose_fuel_conversions`` after ``reconcile_fuel_conversion_caps`` has
        rescaled it. Read-only here; mutates ``fleet`` instead.
    idx
        Current time-step index, used for profile writes and the start of the expense window.
    timeline
        Simulation timeline in dateline units; used to compute the years axis for expense
        booking.
    """

    indices = {vessel.name: i for i, vessel in enumerate(fleet.vessels)}

    _apply_from_side(fleet, proposals, indices, idx, timeline)
    _apply_to_side(fleet, proposals, indices)


def _extract_conversion_source(fleet: Fleet, vessel_from: Vessel, idx: int) -> _ConversionSource | None:
    """
    Bundle the per-source-vessel-type invariants of a propose pass.

    Parameters
    ----------
    fleet
        The fleet instance.
    vessel_from
        Source vessel type.
    idx
        Current time-step index for the expectation lookups.

    Returns
    -------
    The source bundle, or None when no conversion lane is defined for the vessel type.
    """

    conversion_costs = extract_from_tuple_dict(fleet.fuel_conversion_cost, key1=vessel_from.name)
    conversion_costs = {name_to: cost for name_to, cost in conversion_costs.items() if cost is not None}

    if not conversion_costs:
        return None

    return _ConversionSource(vessel_from.name,
                             vessel_from.fuel_type,
                             vessel_from.expectation.get_total_energy(idx),
                             vessel_from.expectation.get_fuel_cost_flow(),
                             vessel_from.expectation.get_capex_npv(idx),
                             conversion_costs)


def _evaluate_increment(fleet: Fleet,
                        vessels: dict[str, Vessel],
                        source: _ConversionSource,
                        avg_age: float,
                        remaining_lifetime_from: float,
                        multiplier: float,
                        supply_excess: dict[FuelTypeID, float],
                        idx: int) -> dict[str, _ConversionCandidate]:
    """
    Evaluate every destination type for one eligible increment and run the DCM on the result.

    Parameters
    ----------
    fleet
        The fleet instance.
    vessels
        Vessel lookup by name.
    source
        Invariants of the source vessel type.
    avg_age
        Average age of the increment.
    remaining_lifetime_from
        Remaining lifetime of the source type at the increment's average age.
    multiplier
        Number of vessels in the increment.
    supply_excess
        Working supply excess per fuel type; read-only here.
    idx
        Current time-step index.

    Returns
    -------
    Candidates keyed by destination name, with conversion counts filled in by the DCM; empty
    when no destination qualifies (the DCM is not invoked).
    """

    candidates = {}

    for name_to, conversion_cost in source.conversion_costs.items():

        if (not fleet.allow_vessel[name_to]) or (not fleet.conversion_available[name_to]):
            continue

        vessel_to = vessels[name_to]
        candidate = _evaluate_candidate(vessel_to, conversion_cost, source, avg_age,
                                        remaining_lifetime_from, multiplier,
                                        supply_excess[vessel_to.fuel_type], idx)
        if candidate is not None:
            candidates[name_to] = candidate

    if not candidates:
        return candidates

    # the BAU sentinel (metric=0., limit=1.) sits at index -1 of the DCM input and is dropped on return
    metrics = [candidate.metric for candidate in candidates.values()] + [0.]
    limits = [candidate.limit for candidate in candidates.values()] + [1.]

    uptakes, _ = calculate_asset_shares(metrics, UtilityID.SIGNED_REFERENCE,
                                        fleet.fuel_conversion_sensitivity.get(),
                                        reference=source.capex_npv, limits=limits)

    # store as conversion counts so reconciliation can scale per-pair without a re-multiply
    for candidate, share in zip(candidates.values(), uptakes):
        candidate.count = share * multiplier

    return candidates


def _evaluate_candidate(vessel_to: Vessel,
                        conversion_cost: Scalar,
                        source: _ConversionSource,
                        avg_age: float,
                        remaining_lifetime_from: float,
                        multiplier: float,
                        supply: float,
                        idx: int) -> _ConversionCandidate | None:
    """
    Evaluate the business case of converting increment vessels to one destination type.

    Parameters
    ----------
    vessel_to
        Destination vessel type.
    conversion_cost
        Lump-sum cost of converting one vessel to the destination type.
    source
        Invariants of the source vessel type.
    avg_age
        Average age of the increment.
    remaining_lifetime_from
        Remaining lifetime of the source type at the increment's average age.
    multiplier
        Number of vessels in the increment.
    supply
        Working supply excess of the destination type's fuel.
    idx
        Current time-step index.

    Returns
    -------
    The evaluated candidate with ``count`` left at zero, or None when the destination type has
    no remaining lifetime or no fuel supply excess.
    """

    remaining_lifetime_to = round(vessel_to.lifetime.get() - avg_age, ROUND_OFF)
    if remaining_lifetime_to <= 0.:
        return None

    if supply <= 0.:
        return None

    discount_rate = vessel_to.cost_of_capital.get()
    energy_per_vessel = vessel_to.expectation.get_total_energy(idx)
    maximum_vessels = supply / energy_per_vessel
    limit = min(maximum_vessels / multiplier, 1.)

    cost_fuel_to = vessel_to.expectation.get_fuel_cost_flow()

    # fuel savings count over the window both the current and the converted
    # vessel type still serve; the conversion cost is a lump sum up front
    common_window = min(remaining_lifetime_from, remaining_lifetime_to)
    cash_flow = (trim_flow_to_lifetime(source.fuel_cost_flow, common_window)
                 - trim_flow_to_lifetime(cost_fuel_to, common_window))
    cash_flow[0] -= conversion_cost.get()

    metric = calculate_net_present_value(cash_flow, discount_rate)

    # for expense reporting the cost is levelized exactly: a constant yearly
    # charge whose NPV over the destination type's remaining lifetime equals
    # the conversion cost
    ones_flow = expand_to_flow(remaining_lifetime_to, 1.)
    charge = conversion_cost.get() / calculate_net_present_value(ones_flow, discount_rate)

    return _ConversionCandidate(metric, limit, energy_per_vessel, charge, remaining_lifetime_to)


def _apply_from_side(fleet: Fleet,
                     proposals: list[_ConversionProposal],
                     indices: dict[str, int],
                     idx: int,
                     timeline: np.ndarray) -> None:
    """
    Decrement source-side multipliers, write the profile, and book transition expenses.

    Parameters
    ----------
    fleet
        The fleet instance.
    proposals
        Finalised proposals.
    indices
        Vessel index lookup by name.
    idx
        Current time-step index.
    timeline
        Simulation timeline in dateline units.
    """

    years_ahead = timeline[idx:] / YEAR
    expenses_ahead = fleet.fuel_conversion_expenses[idx:]

    for proposal in proposals:

        increments_from = fleet.increments[indices[proposal.name_from]]

        for name_to, candidate in proposal.candidates.items():

            if not candidate.count:
                continue

            increments_from[proposal.increment_idx].multiplier -= candidate.count

            # update baseline on oldest increment
            if proposal.increment_idx == 0 and increments_from[0].baseline is not None:
                increments_from[0].baseline -= candidate.count

            fleet.profile.add_fuel_conversions(proposal.name_from, name_to, idx, candidate.count)

            _book_conversion_expenses(expenses_ahead, years_ahead, candidate)


def _book_conversion_expenses(expenses_ahead: np.ndarray,
                              years_ahead: np.ndarray,
                              candidate: _ConversionCandidate) -> None:
    """
    Book the levelized charge over the service window; the coverage prorates the final partial
    year so the booked amounts match the levelization identity.

    Parameters
    ----------
    expenses_ahead
        View of the fleet's fuel-conversion expenses from the conversion step onward; updated in place.
    years_ahead
        Timeline in years from the conversion step onward.
    candidate
        Conversion providing count, charge, and window.
    """

    coverage = np.clip(candidate.window - np.floor(years_ahead - years_ahead[0]), 0., 1.)
    expenses_ahead += candidate.count * candidate.charge * coverage


def _apply_to_side(fleet: Fleet,
                   proposals: list[_ConversionProposal],
                   indices: dict[str, int]) -> None:
    """
    Insert converted vessels on the destination side.

    Runs after every source-side decrement so a vessel converted in this timestep cannot be
    converted again within it.

    Parameters
    ----------
    fleet
        The fleet instance.
    proposals
        Finalised proposals.
    indices
        Vessel index lookup by name.
    """

    for proposal in proposals:

        v_from = indices[proposal.name_from]

        for name_to, candidate in proposal.candidates.items():

            if not candidate.count:
                continue

            # resolve the source increment per insert: earlier inserts may have shifted its list
            increment_from = fleet.increments[v_from][proposal.increment_idx]
            _insert_converted_increment(fleet.increments[indices[name_to]], increment_from,
                                        candidate.count, proposal.age, proposal.dt)


def _insert_converted_increment(increments_to: list[Increment],
                                increment_from: Increment,
                                count: float,
                                age: float,
                                dt: float) -> None:
    """
    Insert a converted-vessel increment into the destination's age-sorted increment list.

    Parameters
    ----------
    increments_to
        Destination increment list, sorted oldest first; mutated in place.
    increment_from
        Source increment providing the technology package and charter rate carried along.
    count
        Number of vessels converted.
    age
        Age of the converted increment.
    dt
        Age-bin width of the converted increment.
    """

    if increments_to:
        ages_to = np.array([increment.age for increment in increments_to])
        idx_to = int(np.searchsorted(-ages_to, -age, side='right'))
    else:
        idx_to = 0

    # the carried technology charter rate rides along unchanged; the amortization window and
    # discount rate stay those of the source vessel type — the same simplification level as
    # disregarding the maintenance cost difference (see perform_fuel_conversions)
    increments_to.insert(idx_to, Increment(count, age, dt,
                                           package_uptake=increment_from.package_uptake.copy(),
                                           technology_charter_rate=increment_from.technology_charter_rate))

    # update baseline on oldest increment
    if idx_to == 0:
        if len(increments_to) > 1 and increments_to[1].baseline is not None:
            increments_to[0].baseline = increments_to[1].baseline + count
            increments_to[1].baseline = None
        else:
            increments_to[0].baseline = count
