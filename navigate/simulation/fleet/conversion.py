# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Fuel conversion of existing vessels, and the fuel-type balance it weighs.

The evaluation runs in three phases per fleet and time-step:

1. ``_propose_fuel_conversions`` computes the proposed conversion counts and changes
   no fleet state.
2. ``_reconcile_fuel_conversion_caps`` scales the proposals to the per-pair flow caps.
3. ``_apply_fuel_conversions`` updates the fleet: multipliers, results and expenses.

The phases communicate through one ``_ConversionProposal`` per (from-type, increment)
cohort, each holding a ``_ConversionCandidate`` per destination type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import FuelTypeID, UtilityID
from navigate.core.increment import VesselIncrement
from navigate.simulation.cohort import find_insertion_index
from navigate.simulation.economics import (
    calculate_asset_shares,
    calculate_net_present_value,
    expand_to_flow,
    trim_flow_to_lifetime,
)
from navigate.simulation.fleet._composition import (
    get_multipliers,
    get_total_multiplier,
    is_retrofit_cycle,
)
from navigate.util import ROUND_OFF, YEAR

if TYPE_CHECKING:
    from collections.abc import Iterator

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray


@dataclass
class _ConversionTarget:
    """
    Per-destination-vessel-type invariants of one conversion lane in a propose pass.

    Parameters
    ----------
    name
        Name of the destination vessel type.
    fuel_type
        Primary fuel type of the destination vessel type.
    lifetime
        Lifetime of the destination vessel type, in years.
    energy_per_vessel
        Energy demand of one destination vessel, in GJ/year.
    fuel_cost_flow
        Expected yearly fuel cost flow of one destination vessel, in USD/year.
    discount_rate
        Discount rate of the destination vessel type, its cost of capital.
    cost
        Lump-sum cost of converting one vessel along the lane, in USD.
    """

    name: str
    fuel_type: FuelTypeID
    lifetime: float
    energy_per_vessel: float
    fuel_cost_flow: FloatArray
    discount_rate: float
    cost: float


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
    lifetime
        Lifetime of the source vessel type, in years.
    energy_per_vessel
        Energy demand of one source vessel, in GJ/year.
    fuel_cost_flow
        Expected yearly fuel cost flow of one source vessel, in USD/year.
    capex_npv
        Summed ship CAPEX NPV, in USD; it non-dimensionalizes the conversion NPV in
        the DCM.
    targets
        Destinations of the open conversion lanes, keyed by vessel-type name.
    """

    name: str
    fuel_type: FuelTypeID
    lifetime: float
    energy_per_vessel: float
    fuel_cost_flow: FloatArray
    capex_npv: float
    targets: dict[str, _ConversionTarget]


@dataclass
class _ConversionCohort:
    """
    One cohort eligible for conversion in a propose pass.

    Parameters
    ----------
    source
        Invariants of the cohort's vessel type.
    increment_idx
        Index of the cohort in its vessel type's increment list.
    increment
        The cohort's increment.
    mean_age
        Mean age of the cohort, in years.
    remaining_lifetime
        Remaining lifetime of the vessel type at the cohort's mean age, in years.
    """

    source: _ConversionSource
    increment_idx: int
    increment: VesselIncrement
    mean_age: float
    remaining_lifetime: float


@dataclass
class _ConversionCandidate:
    """
    One destination vessel type evaluated for conversion out of a cohort.

    Parameters
    ----------
    target
        Invariants of the destination vessel type.
    metric
        Net present value of converting one vessel, in USD.
    limit
        Supply-capped share limit passed to the DCM.
    charge
        Levelized conversion cost per converted vessel, in USD/year.
    window
        Levelization window, the destination type's remaining lifetime, in years.
    count
        Number of vessels proposed to convert; set by the DCM and scaled by the
        reconciliation.
    """

    target: _ConversionTarget
    metric: float
    limit: float
    charge: float
    window: float
    count: float = field(init=False)


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
        Age of the cohort, in years.
    age_span
        Age-bin width of the cohort, in years.
    candidates
        Evaluated candidates, keyed by destination vessel-type name.
    """

    name_from: str
    increment_idx: int
    age: float
    age_span: float
    candidates: dict[str, _ConversionCandidate]


def perform_fuel_conversions(
    fleet: Fleet, timeline: FloatArray, time_step: float, idx: int
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
    timeline
        Simulation timeline, in days.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index.
    """
    if not fleet.can_fuel_convert():
        return

    proposals = _propose_fuel_conversions(fleet, time_step, idx)
    _reconcile_fuel_conversion_caps(fleet, proposals, time_step)
    _apply_fuel_conversions(fleet, proposals, timeline, idx)


def _propose_fuel_conversions(
    fleet: Fleet, time_step: float, idx: int
) -> list[_ConversionProposal]:
    """
    Walk the (from-type, eligible-cohort, to-type) nest to produce conversion counts.

    Changes no fleet state. A working copy of the fuel-type supply excess is debited
    as proposals are gathered, so the DCM's supply cap on each target fuel holds across
    cohorts. The per-pair flow caps are applied later, by
    ``_reconcile_fuel_conversion_caps``.

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
    time_step
        Current time-step size, in days.
    idx
        Current time-step index of the energy and cost-flow lookups.

    Returns
    -------
    list[_ConversionProposal]
        One proposal per (from-type, cohort) pair with a viable business case, in
        walk order.
    """
    # the supply beyond what the fleet can already burn, from the previous step's
    # totals (the results phase writes this step's after this runs); the proposals
    # debit this working copy so the DCM supply cap stays realistic
    supply_excess: dict[FuelTypeID, float] = {}
    for fuel_type in FuelTypeID:
        supply = fleet.expectation.get_fuel_type_supply(fuel_type)
        capacity = fleet.expectation.get_fuel_type_capacity(fuel_type)
        supply_excess[fuel_type] = supply - capacity

    proposals = []

    for cohort in _eligible_cohorts(fleet, time_step, idx):
        candidates = _evaluate_candidates(cohort, supply_excess)
        if not candidates:
            continue

        _choose_conversions(fleet, cohort, candidates)
        _debit_supply_excess(supply_excess, cohort.source, candidates)

        proposal = _ConversionProposal(
            cohort.source.name,
            cohort.increment_idx,
            cohort.increment.age,
            cohort.increment.age_span,
            candidates,
        )
        proposals.append(proposal)

    return proposals


def _reconcile_fuel_conversion_caps(
    fleet: Fleet, proposals: list[_ConversionProposal], time_step: float
) -> None:
    """
    Scale the proposals in place to the per-pair flow caps.

    ``set_fuel_conversion_limit("from", "to", l)`` caps the fraction of the total fleet
    allowed to convert on a (from, to) lane per year:
    ``pair_cap[from, to] = l * time_step / YEAR * existing_total``, where
    ``existing_total`` is the number of vessels in the fleet before newbuilds. The cap
    acts on the pair's summed conversion count; a pair above its cap has every
    cohort scaled to fit.

    Parameters
    ----------
    fleet
        Fleet holding the conversion limits.
    proposals
        Output of ``_propose_fuel_conversions``; its counts are rescaled in place.
    time_step
        Current time-step size, in days.
    """
    # counted before the newbuilds, which are inserted later in the same time-step
    existing_total = get_total_multiplier(fleet)
    dt = time_step / YEAR

    pair_proposed: dict[tuple[str, str], float] = {}
    for proposal, name_to, candidate in _proposed_conversions(proposals):
        pair = (proposal.name_from, name_to)
        pair_proposed[pair] = pair_proposed.get(pair, 0.0) + candidate.count

    pair_scale = {}
    for pair, proposed in pair_proposed.items():
        limit = fleet.fuel_conversion_limits[pair].get()
        pair_cap = limit * dt * existing_total
        if proposed > pair_cap:
            pair_scale[pair] = pair_cap / proposed

    for proposal, name_to, candidate in _proposed_conversions(proposals):
        scale = pair_scale.get((proposal.name_from, name_to))
        if scale is not None:
            candidate.count *= scale


def _apply_fuel_conversions(
    fleet: Fleet, proposals: list[_ConversionProposal], timeline: FloatArray, idx: int
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
        Output of ``_propose_fuel_conversions`` after
        ``_reconcile_fuel_conversion_caps``; read only.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index, where the results are written and the expenses start.
    """
    names = [vessel.name for vessel in fleet.vessels]
    increments = dict(zip(names, fleet.increments, strict=True))

    _apply_from_side(fleet, proposals, increments, timeline, idx)
    _apply_to_side(proposals, increments)


def _eligible_cohorts(
    fleet: Fleet, time_step: float, idx: int
) -> Iterator[_ConversionCohort]:
    """
    Yield the cohorts eligible for conversion, in walk order.

    A cohort is eligible when it is at a retrofit cycle, has reached the minimum
    conversion age, has lifetime left at its mean age and holds vessels, and when an
    open conversion lane starts at its vessel type.

    Parameters
    ----------
    fleet
        Fleet whose vessels may convert.
    time_step
        Current time-step size, in days.
    idx
        Current time-step index of the expectation lookups.

    Yields
    ------
    _ConversionCohort
        Each eligible cohort, vessel type by vessel type, youngest first.
    """
    retrofit_frequency = fleet.retrofit_frequency.get()
    minimum_age = fleet.fuel_conversion_minimum_age.get()
    dt = time_step / YEAR

    vessels = {vessel.name: vessel for vessel in fleet.vessels}

    for vessel_from, increments in zip(fleet.vessels, fleet.increments, strict=True):
        source = _extract_conversion_source(fleet, vessels, vessel_from, idx)
        if source is None:
            continue

        # cohorts are walked youngest to oldest (index 0 is the oldest cohort); when
        # target-fuel supply binds, younger cohorts with longer remaining lifetimes
        # claim the working supply excess first
        for increment_idx, increment in reversed(list(enumerate(increments))):
            if not is_retrofit_cycle(increment.age, retrofit_frequency, dt):
                continue

            mean_age = round(increment.age + increment.age_span / 2.0, ROUND_OFF)
            if mean_age < minimum_age:
                continue

            remaining_lifetime = round(source.lifetime - mean_age, ROUND_OFF)
            if remaining_lifetime <= 0.0:
                continue

            if increment.multiplier <= 0.0:
                continue

            yield _ConversionCohort(
                source, increment_idx, increment, mean_age, remaining_lifetime
            )


def _extract_conversion_source(
    fleet: Fleet, vessels: dict[str, Vessel], vessel_from: Vessel, idx: int
) -> _ConversionSource | None:
    """
    Bundle the per-source-vessel-type invariants of a propose pass.

    A lane is open when its conversion cost is set and its destination is allowed in
    the fleet and available for conversion.

    Parameters
    ----------
    fleet
        Fleet holding the conversion costs and settings.
    vessels
        Vessel types by name.
    vessel_from
        Source vessel type.
    idx
        Current time-step index of the expectation lookups.

    Returns
    -------
    _ConversionSource | None
        The source bundle, or None when no open conversion lane starts at the vessel
        type.
    """
    targets = {}
    for (name_from, name_to), cost in fleet.fuel_conversion_costs.items():
        if name_from != vessel_from.name or cost is None:
            continue

        if not (fleet.allow_vessel[name_to] and fleet.conversion_available[name_to]):
            continue

        targets[name_to] = _extract_conversion_target(vessels[name_to], cost, idx)

    if not targets:
        return None

    return _ConversionSource(
        vessel_from.name,
        vessel_from.primary_fuel_type,
        vessel_from.lifetime.get(),
        vessel_from.expectation.get_total_energy(idx),
        vessel_from.expectation.get_fuel_cost_flow(),
        vessel_from.expectation.get_capex_npv(idx),
        targets,
    )


def _extract_conversion_target(
    vessel_to: Vessel, conversion_cost: ForecastInput, idx: int
) -> _ConversionTarget:
    """
    Bundle the invariants of one conversion lane's destination for a propose pass.

    Parameters
    ----------
    vessel_to
        Destination vessel type.
    conversion_cost
        Cost of converting one vessel along the lane.
    idx
        Current time-step index of the expectation lookups.

    Returns
    -------
    _ConversionTarget
        The destination bundle.
    """
    # a numpy scalar keeps the supply cap's division numpy division: a zero energy
    # gives an unbounded vessel count, not a ZeroDivisionError
    energy_per_vessel = np.float64(vessel_to.expectation.get_total_energy(idx))

    return _ConversionTarget(
        vessel_to.name,
        vessel_to.primary_fuel_type,
        vessel_to.lifetime.get(),
        energy_per_vessel,
        vessel_to.expectation.get_fuel_cost_flow(),
        vessel_to.cost_of_capital.get(),
        conversion_cost.get(),
    )


def _evaluate_candidates(
    cohort: _ConversionCohort, supply_excess: dict[FuelTypeID, float]
) -> dict[str, _ConversionCandidate]:
    """
    Evaluate every destination of the open lanes for one eligible cohort.

    Parameters
    ----------
    cohort
        The eligible cohort.
    supply_excess
        Working supply excess per fuel type, in GJ/year; read only.

    Returns
    -------
    dict[str, _ConversionCandidate]
        Candidates keyed by destination name, their counts still unset; empty when no
        destination qualifies.
    """
    candidates = {}

    for name_to, target in cohort.source.targets.items():
        supply = supply_excess[target.fuel_type]

        candidate = _evaluate_candidate(target, cohort, supply)
        if candidate is not None:
            candidates[name_to] = candidate

    return candidates


def _evaluate_candidate(
    target: _ConversionTarget, cohort: _ConversionCohort, supply: float
) -> _ConversionCandidate | None:
    """
    Evaluate the business case of converting a cohort's vessels to one destination.

    Parameters
    ----------
    target
        Invariants of the destination vessel type.
    cohort
        The eligible cohort.
    supply
        Working supply excess of the destination type's fuel, in GJ/year.

    Returns
    -------
    _ConversionCandidate | None
        The evaluated candidate, its ``count`` still unset, or None when the
        destination type has no remaining lifetime or no fuel supply excess.
    """
    remaining_from = cohort.remaining_lifetime
    remaining_to = round(target.lifetime - cohort.mean_age, ROUND_OFF)
    if remaining_to <= 0.0:
        return None

    if supply <= 0.0:
        return None

    maximum_vessels = supply / target.energy_per_vessel
    limit = min(maximum_vessels / cohort.increment.multiplier, 1.0)

    # fuel savings count over the window both the current and the converted
    # vessel type still serve; the conversion cost is a lump sum up front
    common_window = min(remaining_from, remaining_to)
    fuel_cost_from = trim_flow_to_lifetime(cohort.source.fuel_cost_flow, common_window)
    fuel_cost_to = trim_flow_to_lifetime(target.fuel_cost_flow, common_window)
    cash_flow = fuel_cost_from - fuel_cost_to
    cash_flow[0] -= target.cost
    metric = calculate_net_present_value(cash_flow, target.discount_rate)

    # for expense reporting the cost is levelized exactly: a constant yearly
    # charge whose NPV over the destination type's remaining lifetime equals
    # the conversion cost
    unit_flow = expand_to_flow(remaining_to, 1.0)
    annuity_factor = calculate_net_present_value(unit_flow, target.discount_rate)
    charge = target.cost / annuity_factor

    return _ConversionCandidate(target, metric, limit, charge, remaining_to)


def _choose_conversions(
    fleet: Fleet, cohort: _ConversionCohort, candidates: dict[str, _ConversionCandidate]
) -> None:
    """
    Run the DCM over one cohort's candidates and set their conversion counts.

    Parameters
    ----------
    fleet
        Fleet holding the conversion sensitivity.
    cohort
        The eligible cohort.
    candidates
        Evaluated candidates of the cohort; their counts are set in place.
    """
    # the BAU sentinel (metric=0., limit=1.) sits at index -1 of the DCM input and is
    # dropped on return
    metrics = [candidate.metric for candidate in candidates.values()] + [0.0]
    limits = [candidate.limit for candidate in candidates.values()] + [1.0]
    sensitivity = fleet.fuel_conversion_sensitivity.get()

    shares, _ = calculate_asset_shares(
        metrics,
        UtilityID.SIGNED_REFERENCE,
        sensitivity,
        reference=cohort.source.capex_npv,
        limits=limits,
    )

    # store as conversion counts so reconciliation can scale per-pair without a
    # re-multiply; strict=False drops the BAU sentinel's share
    for candidate, share in zip(candidates.values(), shares, strict=False):
        candidate.count = share * cohort.increment.multiplier


def _debit_supply_excess(
    supply_excess: dict[FuelTypeID, float],
    source: _ConversionSource,
    candidates: dict[str, _ConversionCandidate],
) -> None:
    """
    Debit the working supply excess with one cohort's proposed conversions.

    A converting vessel takes its energy demand from the source fuel type to the
    destination's, so later cohorts and source types see the supply it claims.

    Parameters
    ----------
    supply_excess
        Working supply excess per fuel type, in GJ/year; updated in place.
    source
        Invariants of the source vessel type.
    candidates
        Candidates of the cohort, with their proposed counts.
    """
    for candidate in candidates.values():
        if not candidate.count:
            continue

        energy_from = candidate.count * source.energy_per_vessel
        energy_to = candidate.count * candidate.target.energy_per_vessel

        supply_excess[source.fuel_type] += energy_from
        supply_excess[candidate.target.fuel_type] -= energy_to


def _proposed_conversions(
    proposals: list[_ConversionProposal],
) -> Iterator[tuple[_ConversionProposal, str, _ConversionCandidate]]:
    """
    Yield every proposed conversion with a non-zero count.

    Parameters
    ----------
    proposals
        Proposals to walk, in walk order.

    Yields
    ------
    tuple[_ConversionProposal, str, _ConversionCandidate]
        The proposal, the destination vessel-type name and the candidate.
    """
    for proposal in proposals:
        for name_to, candidate in proposal.candidates.items():
            if candidate.count:
                yield proposal, name_to, candidate


def _apply_from_side(
    fleet: Fleet,
    proposals: list[_ConversionProposal],
    increments: dict[str, list[VesselIncrement]],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Decrement source-side multipliers, write the results, and book transition expenses.

    Parameters
    ----------
    fleet
        Fleet whose vessels convert.
    proposals
        Reconciled proposals.
    increments
        Increment list of each vessel type, keyed by name.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    years_ahead = timeline[idx:] / YEAR
    years_elapsed = np.floor(years_ahead - years_ahead[0])
    expenses_ahead = fleet.fuel_conversion_expenses[idx:]

    for proposal, name_to, candidate in _proposed_conversions(proposals):
        increment_from = increments[proposal.name_from][proposal.increment_idx]
        count = candidate.count

        increment_from.multiplier -= count
        if increment_from.baseline is not None:
            increment_from.baseline -= count

        fleet.results.fuel_conversions[proposal.name_from, name_to][idx] += count

        # the levelized charge is booked over the service window; the coverage
        # prorates the final partial year so the booked amounts match the
        # levelization identity
        coverage = np.clip(candidate.window - years_elapsed, 0.0, 1.0)
        expenses_ahead += count * candidate.charge * coverage


def _apply_to_side(
    proposals: list[_ConversionProposal], increments: dict[str, list[VesselIncrement]]
) -> None:
    """
    Insert converted vessels on the destination side.

    Runs after every source-side decrement so a vessel converted in this time-step
    cannot be converted again within it.

    Parameters
    ----------
    proposals
        Reconciled proposals.
    increments
        Increment list of each vessel type, keyed by name; updated in place.
    """
    for proposal, name_to, candidate in _proposed_conversions(proposals):
        # resolve the source increment per insert: earlier inserts may have shifted
        # its list
        increment_from = increments[proposal.name_from][proposal.increment_idx]
        increments_to = increments[name_to]
        count = candidate.count

        _insert_converted_increment(increments_to, increment_from, proposal, count)


def _insert_converted_increment(
    increments_to: list[VesselIncrement],
    increment_from: VesselIncrement,
    proposal: _ConversionProposal,
    count: float,
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
    proposal
        Proposal the vessels convert under; the converted increment takes its age and
        age span.
    count
        Number of vessels converted.
    """
    idx_to = find_insertion_index(increments_to, proposal.age)

    # the carried technology charter rate rides along unchanged; the amortization window
    # and discount rate stay those of the source vessel type, a simplification of the
    # same order as disregarding the maintenance cost difference (see
    # perform_fuel_conversions)
    increments_to.insert(
        idx_to,
        VesselIncrement(
            count,
            proposal.age,
            proposal.age_span,
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


def calculate_fuel_type_balance(fleet: Fleet, fuels: dict[str, Fuel], idx: int) -> None:
    """
    Calculate the fleet's fuel-type capacity and supply, held on its expectation.

    The next step's fuel conversion weighs each fuel type's supply against its
    capacity.

    Parameters
    ----------
    fleet
        Fleet whose fuel-type capacity and supply are calculated.
    fuels
        All fuels in the simulation.
    idx
        Current time-step index.
    """
    # the reset must come after fleet evolution, which reads the previous step's
    # totals
    fleet.expectation.reset_fuel_type_totals()

    _calculate_fuel_type_capacity(fleet)
    _calculate_fuel_type_supply(fleet, fuels, idx)


def _calculate_fuel_type_capacity(fleet: Fleet) -> None:
    """
    Add the fleet's fuel-type capacity to the fleet expectation.

    The capacity is the energy the fleet's converters spent in the latest
    bunkering solution, counted towards each main fuel type less a dual-fuel
    converter's minimum pilot share, and towards each pilot fuel type at that
    minimum share.

    Parameters
    ----------
    fleet
        Fleet whose fuel-type capacity is added.
    """
    for vessel, multiplier in _vessels_in_service(fleet):
        for converter in vessel.get_converters():
            converter_energy = vessel.expectation.get_spend_energy(converter.name)
            fleet_energy = converter_energy * multiplier

            # pilot fuel counts at its minimum share only: the figure tracks main
            # fuel, and counting all the energy a converter could burn as pilot
            # fuel would inflate the pilot fuel type, usually OIL
            if converter.is_dual_fuel():
                pilot_fuel_share = converter.minimum_pilot_fuel.get()
            else:
                pilot_fuel_share = 0.0

            main_capacity = (1.0 - pilot_fuel_share) * fleet_energy
            pilot_capacity = pilot_fuel_share * fleet_energy

            for fuel_type in converter.main_fuel_types:
                fleet.expectation.add_fuel_type_capacity(fuel_type, main_capacity)

            for fuel_type in converter.pilot_fuel_types:
                fleet.expectation.add_fuel_type_capacity(fuel_type, pilot_capacity)


def _calculate_fuel_type_supply(fleet: Fleet, fuels: dict[str, Fuel], idx: int) -> None:
    """
    Add the fleet's fuel-type supply to the fleet expectation.

    Each vessel's supply is its allocation of the port supplies in the latest
    existing bunkering; an infinite port supply counts in full.

    Parameters
    ----------
    fleet
        Fleet whose fuel-type supply is added.
    fuels
        All fuels in the simulation.
    idx
        Current time-step index.
    """
    for vessel, multiplier in _vessels_in_service(fleet):
        for port, fuel in _port_fuels(vessel, fuels):
            mass = _get_supply_mass(vessel, port, fuel.name, idx)
            lhv = fuel.lower_heating_value.get()
            supply = mass * lhv * multiplier
            fleet.expectation.add_fuel_type_supply(fuel.fuel_type, supply)


def _get_supply_mass(vessel: Vessel, port: Port, fuel_name: str, idx: int) -> float:
    """
    Return the mass of a port's fuel supply that counts for one vessel.

    A finite supply counts as the existing bunkering's allocation to the vessel. The
    bunkering allocates no infinite supply, which counts in full instead: a fuel
    type no active vessel can use yet still has supply to convert to.

    Parameters
    ----------
    vessel
        Vessel holding the allocation.
    port
        Port supplying the fuel.
    fuel_name
        Name of the fuel.
    idx
        Current time-step index.

    Returns
    -------
    float
        Fuel mass counting for one vessel, in tons.
    """
    supply = port.expectation.get_bunker_supply(fuel_name, idx)
    if not np.isfinite(supply):
        return supply

    return vessel.expectation.get_allocation_fuel_existing(port.name, fuel_name)


def _vessels_in_service(fleet: Fleet) -> Iterator[tuple[Vessel, float]]:
    """
    Yield each vessel type of the fleet that has vessels, with its vessel count.

    Parameters
    ----------
    fleet
        Fleet holding the vessel types.

    Yields
    ------
    tuple[Vessel, float]
        The vessel type and its number of vessels.
    """
    for vessel, multiplier in zip(fleet.vessels, get_multipliers(fleet), strict=True):
        if multiplier == 0.0:
            continue

        yield vessel, multiplier


def _port_fuels(vessel: Vessel, fuels: dict[str, Fuel]) -> Iterator[tuple[Port, Fuel]]:
    """
    Yield each port of a vessel's route with each fuel the vessel may bunker there.

    The allocation is per port, so a port the route calls more than once is yielded
    once.

    Parameters
    ----------
    vessel
        Vessel whose route is walked.
    fuels
        All fuels in the simulation.

    Yields
    ------
    tuple[Port, Fuel]
        The port and the fuel.
    """
    for port in dict.fromkeys(vessel.route.ports):
        for fuel in fuels.values():
            if port.bunkering_allowed[fuel.name]:
                yield port, fuel
