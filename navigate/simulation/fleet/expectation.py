# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Deck-derived step-start expectations and the fleet's own evolution forecast."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID
from navigate.simulation.fleet._composition import extract_cargo_miles
from navigate.simulation.fleet._newbuild import is_newbuild_allowed
from navigate.simulation.fleet.scrapping import (
    calculate_survivors,
    group_by_age,
    split_oldest_first,
)
from navigate.util import YEAR, divide_nonzero

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
    Calculate the vessel expectations set once at the start of the step.

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
    slip = converter.slip_fractions[fuel.fuel_type].get()
    effective_lhv = (1.0 - slip) * fuel.lower_heating_value.get()

    vessel.expectation.set_effective_lhv(converter.name, fuel.name, effective_lhv)


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
    slip = converter.slip_fractions[fuel_type].get()

    for emission_name, emission in emissions.items():
        fuel_ttw = fuel.ttw[emission_name].get()
        converter_ttw = converter.consumption_ttw[(fuel_type, emission_name)].get()

        ttw_consumption = (1.0 - slip) * fuel_ttw + converter_ttw
        ttw_slip = slip if emission.fuel_type == fuel_type else 0.0

        key = (converter.name, fuel.name, emission_name)
        expectation.set_ttw_consumption(*key, ttw_consumption)
        expectation.set_ttw_slip(*key, ttw_slip)


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
        effective_lhv = expectation.get_effective_lhv(converter_name, fuel.name)
        lhv_sum += weight * effective_lhv

    lhv = fuel.lower_heating_value.get()
    mean_lhv = lhv_sum / weight_total if weight_total > 0.0 else lhv

    expectation.set_mean_effective_lhv(fuel.name, mean_lhv)


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
            consumption = expectation.get_ttw_consumption(converter_name, *key)
            slip = expectation.get_ttw_slip(converter_name, *key)

            consumption_sum += weight * consumption
            slip_sum += weight * slip

        mean_consumption = consumption_sum / weight_total if weight_total > 0.0 else 0.0
        mean_slip = slip_sum / weight_total if weight_total > 0.0 else 0.0

        expectation.set_mean_ttw_consumption(*key, mean_consumption)
        expectation.set_mean_ttw_slip(*key, mean_slip)


def calculate_fleet_evolution_expectation(
    fleet: Fleet, timeline: FloatArray, idx: int, *, scrapping_pending: bool
) -> None:
    """
    Calculate the multipliers of the existing and expected fleet from this time-step on.

    The existing vessels decline as primary scrapping removes them: each cohort over
    its age span as it passes the vessel lifetime, or at the fleet's fixed scrap rate
    where it sets one. The trade gap this leaves is filled with newbuilds split by the
    memory-weighted recent uptake.

    Parameters
    ----------
    fleet
        Fleet whose expected evolution is calculated.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index, where the expectation starts.
    scrapping_pending
        Whether this time-step's scrapping is still to run. If not, the existing
        multipliers at the time-step are the vessels in the fleet.
    """
    first_pending = 0 if scrapping_pending else 1
    rate = fleet.fixed_scrap_rate

    if rate is None:
        forecast = _forecast_by_age(fleet, timeline, idx, first_pending)
    else:
        forecast = _forecast_at_fixed_rate(fleet, rate, timeline, idx, first_pending)

    existing, newbuild = forecast

    # the expected bunkering needs a multiplier above zero for every allowed vessel
    # type in every nested time-step to return a result per vessel; a small jump
    # start guarantees it while barely moving the fair shares of fuel
    # TODO: make assignable?
    jump_start = 1e-3 * np.sum(existing + newbuild, axis=0)
    for v in np.flatnonzero(is_newbuild_allowed(fleet)):
        absent = existing[v] + newbuild[v] == 0.0
        newbuild[v, absent] = jump_start[absent]

    # the expected newbuilds need no scrapping of their own: the vessels replacing
    # them are expected to follow the same distribution
    expected = existing + newbuild

    expectation = fleet.expectation
    for v, vessel in enumerate(fleet.vessels):
        name = vessel.name
        expectation.set_multiplier(name, BunkerScopeID.EXISTING, idx, existing[v])
        expectation.set_multiplier(name, BunkerScopeID.EXPECTED, idx, expected[v])


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
        Simulation timeline, in days.
    idx
        Current time-step index, where the forecast starts.
    first_pending
        Step of the horizon from which the scrapping is still to run.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Multipliers of the existing vessels and of the newbuilds, of each vessel type
        (rows) over the horizon (columns).
    """
    forward = np.s_[idx:]
    trade = fleet.trade[forward]
    cargo_miles = extract_cargo_miles(fleet.vessels, forward)
    split = _newbuild_split(fleet, idx)

    existing = _existing_by_age(fleet, timeline[forward], first_pending)
    newbuild = _gap_newbuilds(trade, existing, cargo_miles, split)

    return existing, newbuild


def _existing_by_age(fleet: Fleet, times: FloatArray, first_pending: int) -> FloatArray:
    """
    Return the multipliers of the existing vessels, scrapped by age.

    Parameters
    ----------
    fleet
        Fleet whose existing vessels are scrapped.
    times
        Times of the horizon, from the current time-step on, in days.
    first_pending
        Step of the horizon from which the scrapping is still to run.

    Returns
    -------
    FloatArray
        Multipliers of each vessel type (rows) over the horizon (columns).
    """
    existing = np.zeros((len(fleet.vessels), times.size))
    years_ahead = (times - times[0]) / YEAR

    for v, vessel in enumerate(fleet.vessels):
        lifetimes = vessel.lifetime.get(times)

        for increment in fleet.increments[v]:
            survivors = calculate_survivors(increment, lifetimes, years_ahead)

            # with no scrapping left to run at the current time-step, the vessels at
            # or past their lifetime stay in the fleet for it
            survivors[:first_pending] = increment.multiplier

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

    Each time-step scraps the rate's share of the capacity of the fleet expected at
    the time-step before, oldest age group first across vessel types, as primary
    scrapping does; the first time-step scrapped counts the fleet as it is. As the
    expected fleet holds the newbuilds that fill each gap, the time-steps are
    forecast one after another. All ages advance equally, so the age order holds
    over the horizon. Scrapping left once the existing vessels are gone would only
    scrap expected newbuilds, which the gap refills, so it is dropped.

    Parameters
    ----------
    fleet
        Fleet whose evolution is forecast.
    scrap_rate
        Share of the fleet's trade scrapped per year, fraction.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index, where the forecast starts.
    first_pending
        Step of the horizon from which the scrapping is still to run.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Multipliers of the existing vessels and of the newbuilds, of each vessel type
        (rows) over the horizon (columns).
    """
    forward = np.s_[idx:]
    trade = fleet.trade[forward]
    rates = scrap_rate.get(timeline[forward])
    split = _newbuild_split(fleet, idx)

    # the time-steps are rows here, as the forecast runs one time-step at a time
    cargo_miles = extract_cargo_miles(fleet.vessels, forward).T
    existing = np.zeros_like(cargo_miles)
    newbuild = np.zeros_like(cargo_miles)

    grouped = _grouped_multipliers(fleet)
    counted = np.sum(grouped, axis=0)

    for k in range(trade.size):
        is_pending = k >= first_pending

        if is_pending:
            time_step = timeline[idx + k] - timeline[idx + k - 1]
            target = rates[k] * time_step / YEAR * np.dot(counted, cargo_miles[k])
            grouped = _scrap_oldest_groups(grouped, cargo_miles[k], target)

        existing[k] = np.sum(grouped, axis=0)
        newbuild[k] = _gap_newbuilds(trade[k], existing[k], cargo_miles[k], split)

        # a time-step whose evolution has run leaves its gap open, so the next
        # scrapping counts its expected newbuilds only where it is still to run
        counted = existing[k] + newbuild[k] if is_pending else existing[k]

    return existing.T, newbuild.T


def _grouped_multipliers(fleet: Fleet) -> FloatArray:
    """
    Return the multipliers of the fleet's age groups.

    Parameters
    ----------
    fleet
        Fleet whose increments are grouped.

    Returns
    -------
    FloatArray
        Multipliers of each age group (rows), oldest first, of each vessel type
        (columns).
    """
    groups = group_by_age(fleet)
    grouped = np.zeros((len(groups), len(fleet.vessels)))

    for g, group in enumerate(groups):
        for v, i in group:
            grouped[g, v] += fleet.increments[v][i].multiplier

    return grouped


def _scrap_oldest_groups(
    grouped: FloatArray, cargo_miles: FloatArray, capacity: float
) -> FloatArray:
    """
    Return the age groups' multipliers left after scrapping a capacity, oldest first.

    Parameters
    ----------
    grouped
        Multipliers of each age group (rows), oldest first, of each vessel type
        (columns).
    cargo_miles
        Cargo-miles of one vessel of each type, in cargo-miles/year.
    capacity
        Capacity to scrap, in cargo-miles/year.

    Returns
    -------
    FloatArray
        Multipliers of each age group left (rows), oldest first, of each vessel
        type (columns).
    """
    whole, fraction = split_oldest_first(grouped @ cargo_miles, capacity)
    left = grouped[whole:].copy()

    if fraction is not None:
        left[0] *= 1.0 - fraction

    return left


def _gap_newbuilds(
    trade: FloatLike, existing: FloatArray, cargo_miles: FloatArray, split: FloatArray
) -> FloatArray:
    """
    Return the multipliers of the newbuilds expected to fill the trade gap.

    Parameters
    ----------
    trade
        Trade of the fleet, in cargo-miles/year: at one time-step or over several.
    existing
        Multipliers of the existing vessels of each type: at one time-step, or one
        row per type over several.
    cargo_miles
        Cargo-miles of one vessel of each type, in cargo-miles/year, in the shape of
        ``existing``.
    split
        Share of the newbuilds of each vessel type.

    Returns
    -------
    FloatArray
        Multipliers of the newbuilds, in the shape of ``existing``.
    """
    # the multipliers become cargo-miles to take the speed expectations into account
    gap = trade - np.sum(existing * cargo_miles, axis=0)

    # a gap turned negative by falling trade is truncated to zero, which leaves more
    # vessels than trade; where secondary scrapping is allowed this overestimates the
    # fleet
    gap = np.where(gap > 0.0, gap, 0.0)

    newbuild_trade = np.multiply.outer(split, gap)
    return newbuild_trade / cargo_miles


def _newbuild_split(fleet: Fleet, idx: int) -> FloatArray:
    """
    Return the share of the newbuilds each vessel type is expected to take.

    The recent uptake is expected to continue, weighted by memory over the time-steps
    that recorded any. Where no such time-step carries any weight, the current uptake
    is renormalized, in case inertia has reduced it. The weights ignore the time-step
    size, so they misweigh a timeline of varying step sizes.

    Parameters
    ----------
    fleet
        Fleet whose newbuilds are split.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Share of the newbuilds of each vessel type.
    """
    uptakes = fleet.expectation.get_uptakes(idx)
    recorded = np.any(uptakes != 0.0, axis=0)

    steps_back = idx - np.arange(idx + 1)
    decay = fleet.memory.get() ** steps_back
    weights: FloatArray = np.where(recorded, decay, 0.0)

    if np.any(weights):
        return np.sum(uptakes * weights, axis=1) / np.sum(weights)

    current = fleet.current_uptake
    default = 1.0 / len(fleet.vessels)
    return divide_nonzero(current, np.sum(current), default=default)


def calculate_fleet_fuel_demand(fleet: Fleet, fuels: dict[str, Fuel], idx: int) -> None:
    """
    Calculate the fleet's fuel demand over the horizon from the expected bunkering.

    Each vessel's expected bunkered mass is weighted by its expected multiplier.

    Parameters
    ----------
    fleet
        Fleet whose fuel demand is calculated.
    fuels
        All fuels in the simulation.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]
    scope = BunkerScopeID.EXPECTED
    demand: dict[str, FloatLike] = dict.fromkeys(fuels, 0.0)

    for vessel in fleet.vessels:
        expectation = vessel.expectation
        multipliers = fleet.expectation.get_multiplier(vessel.name, scope, forward)

        # the bunkered mass is per port, so a port the route calls more than once
        # counts once
        ports = vessel.route.distinct_ports
        for port, fuel_name in itertools.product(ports, fuels):
            mass = expectation.get_bunker_mass_expected(port.name, fuel_name, forward)
            demand[fuel_name] += multipliers * mass

    for key, value in demand.items():
        fleet.expectation.set_fuel_demand(key, idx, value)
