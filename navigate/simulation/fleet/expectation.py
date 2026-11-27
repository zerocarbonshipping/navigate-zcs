# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Deck-derived step-start expectations and the fleet's own evolution forecast."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID
from navigate.simulation.fleet._composition import extract_cargo_miles, is_in_service
from navigate.simulation.fleet._newbuild import is_newbuild_allowed
from navigate.simulation.fleet.scrapping import (
    calculate_survivors,
    split_oldest_first,
    tabulate_increments,
)
from navigate.util import (
    calculate_kept_fraction,
    calculate_removed_fraction,
    divide_nonzero,
    step_lengths,
    subtract,
)

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_fleet_expectations(
    vessels: dict[str, Vessel], emissions: dict[str, Emission]
) -> None:
    """
    Calculate the vessel expectations derived from the converters and fuels.

    For every vessel and usable fuel, each converter able to burn the fuel gets the
    fuel's effective lower heating value, net of slip, and the TTW emissions of
    burning it, split into the consumption and slip parts. The vessel gets the means
    of these over those converters, weighted by the fuel power each draws.

    Parameters
    ----------
    vessels
        All vessels in the simulation.
    emissions
        All emissions in the simulation.
    """
    for vessel in vessels.values():
        for fuel in vessel.usable_fuels.values():
            converters = vessel.converters_per_fuel[fuel.name]
            weights = _converter_weights(converters)

            for converter in converters.values():
                _calculate_effective_lhv(vessel, converter, fuel)
                _calculate_ttw(vessel, converter, fuel, emissions)

            _calculate_mean_effective_lhv(vessel, weights, fuel)
            _calculate_mean_ttw(vessel, weights, fuel, emissions)


def _calculate_effective_lhv(vessel: Vessel, converter: Converter, fuel: Fuel) -> None:
    """Set the fuel's heating value in the converter net of slip, in GJ/ton fuel-in."""
    slip = converter.slip[fuel.fuel_type].get()
    effective_lhv = (1.0 - slip) * fuel.lower_heating_value.get()

    vessel.expectation.effective_lhv[converter.name, fuel.name] = effective_lhv


def _calculate_ttw(
    vessel: Vessel, converter: Converter, fuel: Fuel, emissions: dict[str, Emission]
) -> None:
    """
    Set the fuel's TTW emissions in the converter, in ton emission/ton fuel-in.

    The consumption part holds the fuel-bound emissions of the burned fraction,
    1 - slip, and the converter's own emissions per ton fuel-in. The slip part is the
    slipped fraction itself, for the emission of the fuel's own type only.
    """
    expectation = vessel.expectation
    fuel_type = fuel.fuel_type
    slip = converter.slip[fuel_type].get()

    for emission_name, emission in emissions.items():
        fuel_ttw = fuel.ttw[emission_name].get()
        converter_ttw = converter.ttw[(fuel_type, emission_name)].get()

        ttw_consumption = (1.0 - slip) * fuel_ttw + converter_ttw
        ttw_slip = slip if emission.slip_fuel_type == fuel_type else 0.0

        key = (converter.name, fuel.name, emission_name)
        expectation.ttw_consumption[key] = ttw_consumption
        expectation.ttw_slip[key] = ttw_slip


def _converter_weights(converters: dict[str, Converter]) -> dict[str, float]:
    """
    Weigh the converters that can burn a fuel by power over efficiency.

    The weight is the fuel power a converter draws at full load, and so estimates its
    share of the vessel's burn of the fuel. A converter with zero efficiency delivers
    no energy and so burns no fuel; it weighs zero.

    Parameters
    ----------
    converters
        Converters able to burn the fuel, by name.

    Returns
    -------
    dict[str, float]
        Weight of each converter by name, in MW.
    """
    weights: dict[str, float] = {}
    for name, converter in converters.items():
        power = converter.power_capacity.get()
        efficiency = converter.efficiency.get()
        weights[name] = power / efficiency if efficiency > 0.0 else 0.0

    return weights


def _calculate_mean_effective_lhv(
    vessel: Vessel, weights: dict[str, float], fuel: Fuel
) -> None:
    """
    Set the vessel's mean effective LHV of the fuel, in GJ/ton fuel-in.

    A vessel without weight on any converter able to burn the fuel has no slip to net
    off, so it takes the fuel's LHV.
    """
    expectation = vessel.expectation
    weight_total = sum(weights.values())
    lhv_sum = 0.0

    for converter_name, weight in weights.items():
        effective_lhv = expectation.effective_lhv[converter_name, fuel.name]
        lhv_sum += weight * effective_lhv

    lhv = fuel.lower_heating_value.get()
    mean_lhv = lhv_sum / weight_total if weight_total > 0.0 else lhv

    expectation.mean_effective_lhv[fuel.name] = mean_lhv


def _calculate_mean_ttw(
    vessel: Vessel,
    weights: dict[str, float],
    fuel: Fuel,
    emissions: dict[str, Emission],
) -> None:
    """
    Set the vessel's mean TTW emissions of the fuel, in ton emission/ton fuel-in.

    A vessel without weight on any converter able to burn the fuel emits nothing
    from it.
    """
    expectation = vessel.expectation
    weight_total = sum(weights.values())

    for emission_name in emissions:
        key = (fuel.name, emission_name)
        consumption_sum = 0.0
        slip_sum = 0.0

        for converter_name, weight in weights.items():
            consumption = expectation.ttw_consumption[converter_name, *key]
            slip = expectation.ttw_slip[converter_name, *key]

            consumption_sum += weight * consumption
            slip_sum += weight * slip

        mean_consumption = consumption_sum / weight_total if weight_total > 0.0 else 0.0
        mean_slip = slip_sum / weight_total if weight_total > 0.0 else 0.0

        expectation.mean_ttw_consumption[key] = mean_consumption
        expectation.mean_ttw_slip[key] = mean_slip


def calculate_fleet_evolution_expectation(
    fleet: Fleet, timeline: FloatArray, idx: int, *, scrapping_pending: bool
) -> None:
    """
    Calculate the existing and expected vessel counts from this time-step on.

    The existing vessels decline as primary scrapping removes them: each cohort over
    its age span as it passes the vessel lifetime, or at the fleet's fixed scrap rate
    where it sets one. The trade gap this leaves is filled with newbuilds split by the
    memory-weighted recent uptake.

    Parameters
    ----------
    fleet
        Fleet whose expected evolution is calculated.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index, where the expectation starts.
    scrapping_pending
        Whether this time-step's scrapping is still to run. If not, the existing
        counts at the time-step are the vessels in the fleet.
    """
    first_pending = 0 if scrapping_pending else 1
    rate = fleet.fixed_scrap_rate

    if rate is None:
        forecast = _forecast_by_age(fleet, timeline, idx, first_pending)
    else:
        forecast = _forecast_at_fixed_rate(fleet, rate, timeline, idx, first_pending)

    existing, newbuild = forecast
    existing = np.where(is_in_service(existing), existing, 0.0)

    # the expected newbuilds need no scrapping of their own: the vessels replacing
    # them are expected to follow the same distribution
    expected = existing + newbuild

    # the expected bunkering needs a count above zero for every allowed vessel
    # type in every nested time-step to return a result per vessel; a small jump
    # start guarantees it while barely moving the fair shares of fuel
    # TODO: make assignable?
    allowed = is_newbuild_allowed(fleet)[:, np.newaxis]
    jump_start = 1e-3 * np.sum(expected, axis=0)
    absent = np.where(allowed, jump_start, 0.0)
    expected = np.where(is_in_service(expected), expected, absent)

    expectation = fleet.expectation
    for v, vessel in enumerate(fleet.vessels):
        name = vessel.name
        expectation.count[name, BunkerScopeID.EXISTING][idx:] = existing[v]
        expectation.count[name, BunkerScopeID.EXPECTED][idx:] = expected[v]


def _forecast_by_age(
    fleet: Fleet, timeline: FloatArray, idx: int, first_pending: int
) -> tuple[FloatArray, FloatArray]:
    """
    Forecast the existing vessels scrapped by age and the newbuilds.

    Parameters
    ----------
    fleet
        Fleet whose evolution is forecast.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index, where the forecast starts.
    first_pending
        Step of the horizon from which the scrapping is still to run.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Number of existing vessels and of newbuilds of each vessel type (rows) over
        the horizon (columns).
    """
    forward = np.s_[idx:]
    trade = fleet.trade[forward]
    cargo_miles = extract_cargo_miles(fleet.vessels, forward)
    split = _newbuild_split(fleet, timeline, idx)

    existing = _existing_by_age(fleet, timeline[forward], first_pending)
    newbuild = _gap_newbuilds(trade, existing, cargo_miles, split)

    return existing, newbuild


def _existing_by_age(fleet: Fleet, times: FloatArray, first_pending: int) -> FloatArray:
    """
    Return the existing vessel counts, scrapped by age.

    Parameters
    ----------
    fleet
        Fleet whose existing vessels are scrapped.
    times
        Times of the horizon, from the current time-step on, in years.
    first_pending
        Step of the horizon from which the scrapping is still to run.

    Returns
    -------
    FloatArray
        Number of vessels of each type (rows) over the horizon (columns).
    """
    existing = np.zeros((len(fleet.vessels), times.size))

    for v, vessel in enumerate(fleet.vessels):
        lifetimes = vessel.lifetime.get(times)

        for increment in fleet.increments[v]:
            survivors = calculate_survivors(increment, lifetimes, times)

            # with no scrapping left to run at the current time-step, the vessels at
            # or past their lifetime stay in the fleet for it
            survivors[:first_pending] = increment.count

            # scrapping never returns vessels, so where the lifetime lengthens again
            # an increment keeps the fewest vessels an earlier time-step left it
            existing[v] += np.minimum.accumulate(survivors)

    return existing


def _forecast_at_fixed_rate(
    fleet: Fleet,
    scrap_rate: ForecastInput,
    timeline: FloatArray,
    idx: int,
    first_pending: int,
) -> tuple[FloatArray, FloatArray]:
    """
    Forecast the existing vessels scrapped at the fixed rate and the newbuilds.

    Each time-step scraps, of the capacity of the fleet expected at the time-step
    before, the share the yearly rate compounds to over the step, the oldest vessels
    first across vessel types, as primary scrapping does; the first time-step
    scrapped counts the fleet as it is. As the expected fleet holds the newbuilds
    that fill each gap, the time-steps are forecast one after another. All ages
    advance together, so each increment's entry interval only shrinks from its
    start as it is scrapped. Scrapping left once the existing vessels are gone would
    only scrap expected newbuilds, which the gap refills, so it is dropped.

    Parameters
    ----------
    fleet
        Fleet whose evolution is forecast.
    scrap_rate
        Share of the fleet's trade scrapped per year, fraction.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index, where the forecast starts.
    first_pending
        Step of the horizon from which the scrapping is still to run.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Number of existing vessels and of newbuilds of each vessel type (rows) over
        the horizon (columns).
    """
    forward = np.s_[idx:]
    trade = fleet.trade[forward]
    rates = scrap_rate.get(timeline[forward])
    split = _newbuild_split(fleet, timeline, idx)

    # the time-steps are rows here, as the forecast runs one time-step at a time
    cargo_miles = extract_cargo_miles(fleet.vessels, forward).T
    existing = np.zeros_like(cargo_miles)
    newbuild = np.zeros_like(cargo_miles)

    type_count = len(fleet.vessels)
    vessel_indices, counts, starts, ends = tabulate_increments(fleet)
    counted = np.bincount(vessel_indices, weights=counts, minlength=type_count)

    for k in range(trade.size):
        is_pending = k >= first_pending

        if is_pending:
            time_step = timeline[idx + k] - timeline[idx + k - 1]
            scrap_share = calculate_removed_fraction(rates[k], time_step)
            target = scrap_share * np.dot(counted, cargo_miles[k])
            capacities = counts * cargo_miles[k][vessel_indices]
            kept, _ = split_oldest_first(starts, ends, capacities, target)

            # the entry interval shrinks from its start with the count, as
            # scrapping oldest first cuts an increment's span
            counts = counts * kept
            starts = ends - (ends - starts) * kept

        existing[k] = np.bincount(vessel_indices, weights=counts, minlength=type_count)
        newbuild[k] = _gap_newbuilds(trade[k], existing[k], cargo_miles[k], split)

        # a time-step whose evolution has run leaves its gap open, so the next
        # scrapping counts its expected newbuilds only where it is still to run
        counted = existing[k] + newbuild[k] if is_pending else existing[k]

    return existing.T, newbuild.T


def _gap_newbuilds(
    trade: FloatLike, existing: FloatArray, cargo_miles: FloatArray, split: FloatArray
) -> FloatArray:
    """
    Return the number of newbuilds expected to fill the trade gap.

    Parameters
    ----------
    trade
        Trade of the fleet, in cargo-miles/year: at one time-step or over several.
    existing
        Number of existing vessels of each type: at one time-step, or one row per
        type over several.
    cargo_miles
        Cargo-miles of one vessel of each type, in cargo-miles/year, in the shape of
        ``existing``.
    split
        Share of the newbuilds of each vessel type.

    Returns
    -------
    FloatArray
        Number of newbuilds of each type, in the shape of ``existing``.
    """
    # the vessel counts become cargo-miles to take the speed expectations into account
    capacity = np.sum(existing * cargo_miles, axis=0)
    gap = subtract(trade, capacity)

    # a gap turned negative by falling trade is truncated to zero, which leaves more
    # vessels than trade; where secondary scrapping is allowed this overestimates the
    # fleet
    gap = np.where(gap > 0.0, gap, 0.0)

    newbuild_trade = np.multiply.outer(split, gap)
    return newbuild_trade / cargo_miles


def _newbuild_split(fleet: Fleet, timeline: FloatArray, idx: int) -> FloatArray:
    """
    Return the share of the newbuilds each vessel type is expected to take.

    The recent uptake is expected to continue, averaged over the time-steps that
    recorded any: each year of a time-step weighs by the memory raised to the years
    since it. Where no such time-step carries any weight, the current uptake is
    renormalized, in case inertia has reduced it.

    Parameters
    ----------
    fleet
        Fleet whose newbuilds are split.
    timeline
        Simulation timeline, in years.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Share of the newbuilds of each vessel type.
    """
    past = np.s_[: idx + 1]
    uptakes = fleet.expectation.uptakes[:, past]
    recorded = np.any(uptakes != 0.0, axis=0)

    memory = fleet.memory.get()
    forgotten = 1.0 - memory
    years_back = timeline[idx] - timeline[past]
    spans = step_lengths(timeline)[past]

    # a time-step's years, each decayed by the memory to the time-step's end; a
    # memory of 1 forgets nothing, so every year counts in full
    decay = calculate_kept_fraction(memory, years_back)
    if forgotten > 0.0:
        remembered_years = (1.0 - calculate_kept_fraction(memory, spans)) / forgotten
    else:
        remembered_years = spans
    weights: FloatArray = np.where(recorded, decay * remembered_years, 0.0)

    if np.any(weights):
        return np.sum(uptakes * weights, axis=1) / np.sum(weights)

    current = fleet.current_uptake
    default = 1.0 / len(fleet.vessels)
    return divide_nonzero(current, np.sum(current), default=default)


def calculate_fleet_bunker_demand(fleet: Fleet, idx: int) -> None:
    """
    Calculate the fleet's demand for each fuel at each port over the horizon.

    The demand is the expected bunkering: each vessel's expected bunkered mass at a
    port, weighted by its expected count. It is kept per port, as the fuel producers
    weigh it against the supply each port receives.

    Parameters
    ----------
    fleet
        Fleet whose bunker demand is calculated.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]
    scope = BunkerScopeID.EXPECTED
    bunker_demand = fleet.expectation.bunker_demand
    demand: dict[tuple[str, str], FloatLike] = dict.fromkeys(bunker_demand, 0.0)

    for vessel in fleet.vessels:
        counts = fleet.expectation.count[vessel.name, scope][forward]

        for key, mass in vessel.expectation.bunker_mass_expected.items():
            demand[key] += counts * mass[forward]

    bunker_demand.at[idx:] = demand
