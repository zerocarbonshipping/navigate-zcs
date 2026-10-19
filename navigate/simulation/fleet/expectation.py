# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Expectations the fleet sets for later phases and other domains."""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID
from navigate.simulation.fleet.composition import (
    extract_cargo_miles_timeline,
    get_multiplier,
)
from navigate.util import YEAR, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel
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
            weights = _converter_weights(vessel, fuel)

            for converter, _ in weights:
                _calculate_effective_lhv(vessel, converter, fuel)
                _calculate_ttw(vessel, converter, fuel, emissions)

            _calculate_mean_effective_lhv(vessel, weights, fuel)
            _calculate_mean_ttw(vessel, weights, fuel, emissions)


def _calculate_effective_lhv(vessel: Vessel, converter: Converter, fuel: Fuel) -> None:
    """Set the fuel's heating value in the converter net of slip, in GJ/ton fuel-in."""
    slip = converter.slip_fraction[fuel.fuel_type].get()
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
    slip = converter.slip_fraction[fuel_type].get()

    for emission_name, emission in emissions.items():
        fuel_ttw = fuel.ttw[emission_name].get()
        converter_ttw = converter.consumption_ttw[(fuel_type, emission_name)].get()

        ttw_consumption = (1.0 - slip) * fuel_ttw + converter_ttw
        ttw_slip = slip if emission.fuel_type == fuel_type else 0.0

        key = (converter.name, fuel.name, emission_name)
        expectation.set_ttw_consumption(*key, ttw_consumption)
        expectation.set_ttw_slip(*key, ttw_slip)


def _converter_weights(vessel: Vessel, fuel: Fuel) -> list[tuple[Converter, float]]:
    """
    Weigh the vessel's converters that can burn a fuel by power over efficiency.

    The weight is the fuel power a converter draws at full load, and so estimates its
    share of the vessel's burn of the fuel. Converters that cannot burn the fuel are
    left out, so they carry no weight in a mean over the weights. A converter with zero
    efficiency delivers no energy and so burns no fuel; it weighs zero.

    Parameters
    ----------
    vessel
        Vessel whose converters are weighed.
    fuel
        Fuel being burned.

    Returns
    -------
    list[tuple[Converter, float]]
        Each converter able to burn the fuel with its weight, in MW.
    """
    weights: list[tuple[Converter, float]] = []
    for converter in vessel.converters_per_fuel[fuel.name].values():
        power = converter.power_capacity.get()
        efficiency = converter.efficiency.get()
        weight = power / efficiency if efficiency > 0.0 else 0.0

        weights.append((converter, weight))

    return weights


def _calculate_mean_effective_lhv(
    vessel: Vessel, weights: list[tuple[Converter, float]], fuel: Fuel
) -> None:
    """
    Set the vessel's mean effective LHV of the fuel, in GJ/ton fuel-in.

    A vessel without weight on any converter able to burn the fuel has no slip to net
    off, so it takes the fuel's LHV.
    """
    expectation = vessel.expectation
    lhv_sum = 0.0
    weight_total = 0.0

    for converter, weight in weights:
        effective_lhv = expectation.get_effective_lhv(converter.name, fuel.name)
        lhv_sum += weight * effective_lhv
        weight_total += weight

    lhv = fuel.lower_heating_value.get()
    mean_lhv = lhv_sum / weight_total if weight_total > 0.0 else lhv

    expectation.set_mean_effective_lhv(fuel.name, mean_lhv)


def _calculate_mean_ttw(
    vessel: Vessel,
    weights: list[tuple[Converter, float]],
    fuel: Fuel,
    emissions: dict[str, Emission],
) -> None:
    """
    Set the vessel's mean TTW emissions of the fuel, in ton emission/ton fuel-in.

    A vessel without weight on any converter able to burn the fuel emits nothing
    from it.
    """
    expectation = vessel.expectation

    for emission_name in emissions:
        key = (fuel.name, emission_name)
        consumption_sum = 0.0
        slip_sum = 0.0
        weight_total = 0.0

        for converter, weight in weights:
            consumption = expectation.get_ttw_consumption(converter.name, *key)
            slip = expectation.get_ttw_slip(converter.name, *key)

            consumption_sum += weight * consumption
            slip_sum += weight * slip
            weight_total += weight

        mean_consumption = consumption_sum / weight_total if weight_total > 0.0 else 0.0
        mean_slip = slip_sum / weight_total if weight_total > 0.0 else 0.0

        expectation.set_mean_ttw_consumption(*key, mean_consumption)
        expectation.set_mean_ttw_slip(*key, mean_slip)


def calculate_fleet_evolution_expectation(
    fleet: Fleet, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the multipliers of the existing and expected fleet from this time-step on.

    The existing vessels decline by their expected scrapping; the trade gap this
    leaves is filled with newbuilds split by the memory-weighted recent uptake.

    Parameters
    ----------
    fleet
        Fleet whose expected evolution is calculated.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index, where the expectation starts.
    """
    idx_ = np.s_[idx:]
    times = timeline[idx_] / YEAR
    future = times - times[0]

    nv = len(fleet.vessels)
    existing = np.zeros((nv, times.size))

    for v, (vessel, incs) in enumerate(
        zip(fleet.vessels, fleet.increments, strict=True)
    ):
        if not incs:
            continue

        multipliers = np.array([inc.multiplier for inc in incs])
        ages = np.array([inc.age for inc in incs])

        lifetime = vessel.lifetime.get()

        # each increment reaches its lifetime after lifetime - age years, oldest
        # first, so the cumulative sum is the expected scrapping to date
        cum_increments = np.cumsum(multipliers)
        cum_increments = np.interp(future, (lifetime - ages), cum_increments, left=0.0)

        existing[v, :] = get_multiplier(fleet, v)
        existing[v, :] -= cum_increments

    # the multipliers become cargo-miles to take the speed expectations into account
    cargo_miles = extract_cargo_miles_timeline(fleet.vessels, idx_)
    existing_trade = np.zeros_like(existing)
    for v in range(nv):
        existing_trade[v, :] = existing[v, :] * cargo_miles[v]

    gap = fleet.trade[idx_] - np.sum(existing_trade, axis=0)

    # a gap turned negative by falling trade is truncated to zero, which leaves more
    # vessels than trade; where secondary scrapping is allowed this overestimates the
    # fleet
    gap = np.where(gap > 0.0, gap, 0.0)

    # the gap is filled on the expectation that the recent uptake continues, weighted
    # by memory, with the current uptake renormalized in case inertia has reduced it;
    # the weights ignore the time-step size, so they misweigh a timeline of varying
    # step sizes
    index = np.arange(idx + 1)
    weights = fleet.memory.get() ** (idx - index)

    uptakes = fleet.expectation.get_uptakes(idx)
    for i in range(idx + 1):
        if np.all(uptakes[:, i] == 0.0):
            weights[i] = 0.0

    if np.any(weights) > 0.0:
        weighted_uptakes = np.sum(uptakes * weights[np.newaxis, :], axis=1)
        weighted_uptakes /= np.sum(weights)
    else:
        weighted_uptakes = divide_nonzero(
            fleet.current_uptake, np.sum(fleet.current_uptake), default=1.0 / nv
        )

    newbuild_trade = np.outer(weighted_uptakes, gap)
    newbuild = np.zeros_like(newbuild_trade)
    for v in range(nv):
        newbuild[v, :] = newbuild_trade[v, :] / cargo_miles[v]

    # the expected bunkering needs a multiplier above zero for every allowed vessel
    # type in every nested time-step to return a result per vessel; a small jump
    # start guarantees it while barely moving the fair shares of fuel
    # TODO: make assignable?
    jump_start_rel = 1e-3
    total_multipliers = np.sum(existing + newbuild, axis=0)
    jump_start = jump_start_rel * total_multipliers
    for v, vessel in enumerate(fleet.vessels):
        if fleet.allow_vessel[vessel.name] and fleet.newbuild_available[vessel.name]:
            non_existent = np.where(existing[v, :] + newbuild[v, :] == 0.0)
            newbuild[v, non_existent] = jump_start[non_existent]

    # the expected newbuilds need no scrapping of their own beyond the vessel
    # lifetime: the vessels replacing them are expected to follow the same
    # distribution
    expected = existing + newbuild
    expectation = fleet.expectation

    for v, vessel in enumerate(fleet.vessels):
        name = vessel.name
        expectation.set_multiplier(idx, name, BunkerScopeID.EXISTING, existing[v, :])
        expectation.set_multiplier(idx, name, BunkerScopeID.EXPECTED, expected[v, :])


def calculate_fleet_fuel_demand(fleet: Fleet, fuels: dict[str, Fuel], idx: int) -> None:
    """
    Calculate the fleet's fuel demand over the horizon from the expected bunkering.

    Each vessel's expected bunkered mass is weighted by its expected multiplier.

    Parameters
    ----------
    fleet
        Fleet instance.
    fuels
        All fuels in the simulation.
    idx
        Current time-step index.
    """
    horizon = np.s_[idx:]
    scope = BunkerScopeID.EXPECTED
    demand: dict[str, FloatLike] = dict.fromkeys(fuels, 0.0)

    for vessel in fleet.vessels:
        expectation = vessel.expectation
        multipliers = fleet.expectation.get_multiplier(vessel.name, scope, horizon)

        # the bunkered mass is per port, so a port the route calls more than once
        # counts once
        ports = dict.fromkeys(vessel.route.ports)
        for port, fuel_name in itertools.product(ports, fuels):
            mass = expectation.get_bunker_mass_expected(port.name, fuel_name, horizon)
            demand[fuel_name] += multipliers * mass

    for key, value in demand.items():
        fleet.expectation.set_fuel_demand(idx, key, value)
