# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Emission factors and coefficients of policies, regulation thresholds, levy costs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import LevySchemeID, PolicyScopeID
from navigate.util import (
    TON_PER_GJ_TO_GRAM_PER_MJ,
    list_intersection,
    unique_list,
)

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_policy_emission_coefficients(
    regulations: dict[str, Regulation],
    levies: dict[str, Levy],
    vessels: dict[str, Vessel],
    plants: dict[str, Plant],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the active policies' coefficients, regulation thresholds and levy costs.

    Combinations span regulations, levies, vessels, fuels, and emissions. A policy's
    WTT and TTW emission factors add up to its emission factors, and these, summed over
    its emissions, to the emission coefficients that convert a ton of fuel to a ton of
    emissions. A levy's coefficients, priced at its level, give its cost per ton of
    fuel.

    Reads the plants' production and delivery WTT, the ports' shore-power emission
    factors, the vessels' effective LHVs and the levies' levels of the current time
    step, so it runs after those are calculated.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    levies
        All levies in the simulation.
    vessels
        All vessels in the simulation.
    plants
        All plants in the simulation.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    plants_by_fuel: dict[str, list[Plant]] = {}
    for plant in plants.values():
        plants_by_fuel.setdefault(plant.fuel.name, []).append(plant)

    for regulation in regulations.values():
        if not regulation.active:
            continue

        _calculate_regulation(regulation, vessels, plants_by_fuel, times, idx)

    for levy in levies.values():
        if not levy.active:
            continue

        _calculate_levy(levy, vessels, plants_by_fuel, times, idx)


def _calculate_regulation(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    times: FloatArray,
    idx: int,
) -> None:
    """
    Calculate a regulation's emission factors, coefficients and vessel thresholds.

    The regulation's scope decides which of the WTT and TTW emission factors it gets.
    From the factors follow its emission coefficients; its shore-power coefficients and
    vessel thresholds are calculated alongside.

    Parameters
    ----------
    regulation
        Regulation whose factors, coefficients and thresholds are calculated.
    vessels
        All vessels in the simulation.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    scope = regulation.scope

    if scope in (PolicyScopeID.WTT, PolicyScopeID.WTW):
        _calculate_regulation_wtt(regulation, vessels, plants_by_fuel, times, idx)

    if scope in (PolicyScopeID.TTW, PolicyScopeID.WTW):
        _calculate_regulation_ttw(regulation, vessels, times, idx)

    _calculate_regulation_emission_coefficients(regulation, vessels, idx)
    _calculate_regulation_shore_power_coefficients(regulation, vessels, idx)
    _calculate_regulation_vessel_thresholds(regulation, times, idx)


def _calculate_regulation_wtt(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    times: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the WTT emission factors of a regulation.

    Unless the regulation supplies a WTT, a vessel's factor is the mean of the port
    estimates over every port on its route, each counted once, as the vessel may
    bunker a fuel outside the jurisdiction and burn it inside. A fuel no route port
    has an estimate for gets a NaN factor.

    Parameters
    ----------
    regulation
        Regulation whose WTT emission factors are calculated.
    vessels
        All vessels in the simulation.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    supplied = _evaluate_supplied(regulation, regulation.fuel_wtt, times)

    for vessel_name, vessel in vessels.items():
        # a vessel with no port in the jurisdiction is never policed, so never read
        if not regulation.in_jurisdiction_vessel[vessel_name]:
            continue

        ports = unique_list(vessel.route.ports)

        for fuel in _target_fuels(regulation, vessel):
            plants = plants_by_fuel.get(fuel.name, [])

            for emission in regulation.emissions:
                key = (fuel.name, emission.name)
                wtt = supplied[key]
                if wtt is None:
                    wtt = _average_wtt_over_route(ports, fuel, emission, plants, idx)

                factor = _apply_gwp(wtt, regulation, emission)
                expectation.set_wtt(idx, (vessel_name, *key), factor)


def _calculate_regulation_ttw(
    regulation: Regulation, vessels: dict[str, Vessel], times: FloatArray, idx: int
) -> None:
    """
    Calculate the TTW emission factors of a regulation.

    Each converter able to burn a fuel on each vessel gets its own consumption and slip
    factors, read from the vessel's expectation unless the regulation supplies a TTW.

    Parameters
    ----------
    regulation
        Regulation whose TTW emission factors are calculated.
    vessels
        All vessels in the simulation.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    supplied = _evaluate_supplied(regulation, regulation.fuel_ttw, times)

    for vessel_name, vessel in vessels.items():
        for converter_name, fuel in _target_converter_fuels(regulation, vessel):
            for emission in regulation.emissions:
                key = (vessel_name, converter_name, fuel.name, emission.name)
                ttw = supplied[(fuel.name, emission.name)]

                if ttw is None:
                    consumption, slip = _converter_ttw(regulation, vessel, key)
                else:
                    # TODO: change if deciding to split input
                    consumption, slip = ttw, 0.0

                factor_consumption = _apply_gwp(consumption, regulation, emission)
                factor_slip = _apply_gwp(slip, regulation, emission)

                expectation.set_ttw_consumption(idx, key, factor_consumption)
                expectation.set_ttw_slip(idx, key, factor_slip)


def _calculate_regulation_emission_coefficients(
    regulation: Regulation, vessels: dict[str, Vessel], idx: int
) -> None:
    """
    Calculate the emission coefficients of a regulation.

    Parameters
    ----------
    regulation
        Regulation whose emission coefficients are calculated.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation

    for vessel_name, vessel in vessels.items():
        for converter_name, fuel in _target_converter_fuels(regulation, vessel):
            key = (vessel_name, converter_name, fuel.name)
            coefficient = _calculate_regulation_coefficient(regulation, key, idx)

            # a NaN WTT factor, where no route port has an estimate for the fuel,
            # leaves the fuel without a coefficient; no route port then supplies it,
            # so the LP spends none of it and reads the missing coefficient as zero
            if np.isnan(coefficient).any():
                continue

            expectation.set_emission_coefficient(idx, key, coefficient)


def _calculate_regulation_coefficient(
    regulation: Regulation, key: tuple[str, str, str], idx: int
) -> FloatLike:
    """
    Calculate the regulation's emission coefficient of a fuel burned in a converter.

    The coefficient sums, over the regulation's emissions, the fuel's WTT factor on
    the vessel and its TTW factors in the converter.

    Parameters
    ----------
    regulation
        Regulation whose emission coefficient is calculated.
    key
        Names of the vessel, the converter and the fuel the coefficient is stored under.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Emission coefficient from `idx` onward, in ton emission/ton fuel.
    """
    vessel_name, converter_name, fuel_name = key
    coefficient = 0.0

    for emission in regulation.emissions:
        key_wtt = (vessel_name, fuel_name, emission.name)
        key_ttw = (vessel_name, converter_name, fuel_name, emission.name)
        coefficient += _calculate_emission_factor(regulation, key_wtt, key_ttw, idx)

    return coefficient


def _calculate_regulation_shore_power_coefficients(
    regulation: Regulation, vessels: dict[str, Vessel], idx: int
) -> None:
    """
    Calculate the regulation's shore-power emission coefficient at each route port.

    Parameters
    ----------
    regulation
        Regulation whose shore-power emission coefficients are calculated.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    forward = np.s_[idx:]

    route_ports = (port for vessel in vessels.values() for port in vessel.route.ports)

    for port in unique_list(route_ports):
        get_emission_factor = port.expectation.get_shore_power_emission_factor

        coefficient = 0.0
        for emission in regulation.emissions:
            factor = get_emission_factor(emission.name, forward)
            coefficient += _apply_gwp(factor, regulation, emission)

        expectation.set_shore_power_emission_coefficient(idx, port.name, coefficient)


def _calculate_regulation_vessel_thresholds(
    regulation: Regulation, times: FloatArray, idx: int
) -> None:
    """
    Calculate the threshold each vessel must satisfy, zero where it is not policed.

    Parameters
    ----------
    regulation
        Regulation whose vessel thresholds are calculated.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation

    for vessel_name, threshold in regulation.vessel_threshold.items():
        # zero rather than unwritten: an event can stop the regulation policing the
        # vessel, and the threshold written while it did would remain;
        # check_consistency guarantees every policed vessel a threshold
        if not regulation.vessel_is_policed(vessel_name) or threshold is None:
            expectation.set_vessel_threshold(idx, vessel_name, 0.0)
            continue

        expectation.set_vessel_threshold(idx, vessel_name, threshold.get(times))


def _calculate_levy(
    levy: Levy,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    times: FloatArray,
    idx: int,
) -> None:
    """
    Calculate a levy's emission factors and its costs.

    The levy's scope decides which of the WTT and TTW emission factors it gets. From
    the factors follow its costs.

    Parameters
    ----------
    levy
        Levy whose emission factors and costs are calculated.
    vessels
        All vessels in the simulation.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    scope = levy.scope

    if scope in (PolicyScopeID.WTT, PolicyScopeID.WTW):
        _calculate_levy_wtt(levy, plants_by_fuel, times, idx)

    if scope in (PolicyScopeID.TTW, PolicyScopeID.WTW):
        _calculate_levy_ttw(levy, vessels, times, idx)

    _calculate_levy_costs(levy, vessels, times, idx)


def _calculate_levy_wtt(
    levy: Levy,
    plants_by_fuel: dict[str, list[Plant]],
    times: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the WTT emission factors of a levy.

    Unless the levy supplies a WTT, the factor at each jurisdiction port is the port
    estimate, NaN where the port has none. A port that disallows bunkering the fuel
    gets no factor, as no vessel bunkers the fuel there.

    Parameters
    ----------
    levy
        Levy whose WTT emission factors are calculated.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = levy.expectation
    supplied = _evaluate_supplied(levy, levy.fuel_wtt, times)

    for fuel in levy.fuels:
        plants = plants_by_fuel.get(fuel.name, [])

        for emission in levy.emissions:
            key = (fuel.name, emission.name)

            for port in levy.jurisdiction:
                if not port.bunkering_allowed[fuel.name]:
                    continue

                wtt = supplied[key]
                if wtt is None:
                    wtt = _estimate_port_wtt(port, fuel, emission, plants, idx)

                factor = _apply_gwp(wtt, levy, emission)
                expectation.set_wtt(idx, (port.name, *key), factor)


def _calculate_levy_ttw(
    levy: Levy, vessels: dict[str, Vessel], times: FloatArray, idx: int
) -> None:
    """
    Calculate the TTW emission factors of a levy.

    Each targeted fuel a vessel can use gets its mean consumption and slip factors over
    its converters, read from the vessel's expectation unless the levy supplies a TTW.

    Parameters
    ----------
    levy
        Levy whose TTW emission factors are calculated.
    vessels
        All vessels in the simulation.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = levy.expectation
    supplied = _evaluate_supplied(levy, levy.fuel_ttw, times)

    for vessel_name, vessel in vessels.items():
        for fuel in _target_fuels(levy, vessel):
            for emission in levy.emissions:
                key = (vessel_name, fuel.name, emission.name)
                ttw = supplied[(fuel.name, emission.name)]

                if ttw is None:
                    consumption, slip = _mean_ttw(levy, vessel, key)
                else:
                    # TODO: change if deciding to split input
                    consumption, slip = ttw, 0.0

                factor_consumption = _apply_gwp(consumption, levy, emission)
                factor_slip = _apply_gwp(slip, levy, emission)

                expectation.set_ttw_consumption(idx, key, factor_consumption)
                expectation.set_ttw_slip(idx, key, factor_slip)


def _calculate_levy_costs(
    levy: Levy, vessels: dict[str, Vessel], times: FloatArray, idx: int
) -> None:
    """
    Calculate the levy's cost per ton of each fuel a vessel bunkers in its ports.

    The cost is the levy's level times the fuel's threshold-adjusted emission
    coefficient, from the current time step onward, and zero for a vessel the levy
    does not police.

    Parameters
    ----------
    levy
        Levy whose costs are calculated.
    vessels
        All vessels in the simulation.
    times
        Remaining timeline, in days.
    idx
        Current time-step index.
    """
    expectation = levy.expectation
    scheme = levy.scheme
    forward = np.s_[idx:]

    level = expectation.get_level(forward)
    lower = levy.lower_threshold.get(times)
    upper = None if levy.upper_threshold is None else levy.upper_threshold.get(times)

    for vessel_name, vessel in vessels.items():
        ports = list_intersection(vessel.route.ports, levy.jurisdiction)
        if not ports:
            continue

        policed = levy.vessel_is_policed(vessel_name)

        for fuel in _target_fuels(levy, vessel):
            lhv = vessel.expectation.get_mean_effective_lhv(fuel.name)

            for port in ports:
                if not port.bunkering_allowed[fuel.name]:
                    continue

                key = (vessel_name, port.name, fuel.name)

                # zero rather than unwritten: an event can stop the levy policing
                # the vessel, and the cost written while it did would remain
                if not policed:
                    expectation.set_cost(idx, key, 0.0)
                    continue

                coefficient = _calculate_levy_coefficient(levy, key, idx)

                # a NaN WTT factor, where the port has no estimate for the fuel,
                # leaves the fuel without a cost there; the port then has no supply
                # of it, so the LP bunkers none of it there and reads the cost as zero
                if np.isnan(coefficient).any():
                    continue

                coefficient = _apply_thresholds(coefficient, scheme, lhv, lower, upper)
                expectation.set_cost(idx, key, level * coefficient)


def _calculate_levy_coefficient(
    levy: Levy, key: tuple[str, str, str], idx: int
) -> FloatLike:
    """
    Calculate the levy's emission coefficient of a fuel a vessel bunkers at a port.

    The coefficient sums, over the levy's emissions, the fuel's WTT factor at the
    port and its TTW factors on the vessel.

    Parameters
    ----------
    levy
        Levy whose emission coefficient is calculated.
    key
        Names of the vessel, the port and the fuel the cost is stored under.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Emission coefficient from `idx` onward, in ton emission/ton fuel.
    """
    vessel_name, port_name, fuel_name = key
    coefficient = 0.0

    for emission in levy.emissions:
        key_wtt = (port_name, fuel_name, emission.name)
        key_ttw = (vessel_name, fuel_name, emission.name)
        coefficient += _calculate_emission_factor(levy, key_wtt, key_ttw, idx)

    return coefficient


def _apply_thresholds(
    coefficient: FloatLike,
    scheme: LevySchemeID,
    effective_lhv: float,
    lower: FloatArray,
    upper: FloatArray | None,
) -> FloatLike:
    """
    Adjust a levy emission coefficient to the levy's thresholds and scheme.

    The thresholds are intensities per GJ of effective energy, (1 - slip) * LHV, and
    are converted to ton emission/ton fuel on that basis before they are applied. A
    fuel whose converters slip all of it delivers no energy, so both thresholds
    convert to zero and the excess is the whole coefficient before the scheme and the
    upper threshold apply.

    Parameters
    ----------
    coefficient
        Emission coefficient, in ton emission/ton fuel.
    scheme
        Scheme of the levy.
    effective_lhv
        Effective lower heating value of the fuel on the vessel, in GJ/ton fuel.
    lower
        Lower emission factor threshold over the remaining timeline, in kg emission/GJ.
    upper
        Upper emission factor threshold over the remaining timeline, in kg emission/GJ;
        None where the levy has no upper threshold.

    Returns
    -------
    FloatLike
        Levied part of the emission coefficient, in ton emission/ton fuel.
    """
    intensity_to_coefficient = effective_lhv / TON_PER_GJ_TO_GRAM_PER_MJ
    excess = coefficient - lower * intensity_to_coefficient

    if scheme == LevySchemeID.SUBSIDY:
        return np.minimum(excess, 0.0)

    if scheme == LevySchemeID.PENALTY:
        excess = np.maximum(excess, 0.0)

    if upper is None:
        return excess

    return np.minimum(excess, (upper - lower) * intensity_to_coefficient)


def _average_wtt_over_route(
    ports: list[Port], fuel: Fuel, emission: Emission, plants: list[Plant], idx: int
) -> FloatLike:
    """
    Estimate a vessel's WTT emissions of a fuel as the mean over its route ports.

    The mean weighs equally the ports that allow bunkering the fuel and have an
    estimate for it. A port listed twice counts twice, so callers pass each port once.
    Where no port contributes, the result is NaN.

    Parameters
    ----------
    ports
        Ports on the vessel's route whose estimates are averaged, each listed once.
    fuel
        Fuel whose WTT emissions are estimated.
    emission
        Emission the estimate is for.
    plants
        Plants producing the fuel, whose WTT the port estimates read.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Approximate WTT from `idx` onward, in ton emission/ton fuel.
    """
    estimates = []
    for port in ports:
        if not port.bunkering_allowed[fuel.name]:
            continue

        estimate = _estimate_port_wtt(port, fuel, emission, plants, idx)

        # a port is left out whole where its estimate is NaN anywhere: a plant
        # estimate is NaN at every step or at none, and only a deck's overwrite
        # could mix the two
        if np.isnan(estimate).any():
            continue

        estimates.append(estimate)

    if not estimates:
        return np.nan

    return np.stack(estimates).mean(axis=0)


def _converter_ttw(
    regulation: Regulation, vessel: Vessel, key: tuple[str, str, str, str]
) -> tuple[float, float]:
    """
    Return the consumption and slip TTW of burning a fuel in a vessel's converter.

    Parameters
    ----------
    regulation
        Regulation the TTW is read for; where it leaves out slip, the slip TTW is zero.
    vessel
        Vessel whose converter TTW is read.
    key
        Names of the vessel, the converter, the fuel and the emission the factors are
        stored under; the vessel's own TTW is keyed by all but the first.

    Returns
    -------
    tuple[float, float]
        Consumption TTW and slip TTW, in ton emission/ton fuel-in.
    """
    expectation = vessel.expectation
    vessel_key = key[1:]

    consumption = expectation.get_ttw_consumption(*vessel_key)
    slip = expectation.get_ttw_slip(*vessel_key) if regulation.include_slip else 0.0

    return consumption, slip


def _mean_ttw(
    levy: Levy, vessel: Vessel, key: tuple[str, str, str]
) -> tuple[float, float]:
    """
    Return the vessel's mean consumption and slip TTW of burning a fuel.

    A levy prices the fuel a vessel bunkers, whichever converter burns it, so it reads
    the vessel's means over its converters rather than each converter's TTW.

    Parameters
    ----------
    levy
        Levy the TTW is read for; where it leaves out slip, the slip TTW is zero.
    vessel
        Vessel whose mean TTW is read.
    key
        Names of the vessel, the fuel and the emission the factors are stored under;
        the vessel's own TTW is keyed by all but the first.

    Returns
    -------
    tuple[float, float]
        Consumption TTW and slip TTW, in ton emission/ton fuel-in.
    """
    expectation = vessel.expectation
    vessel_key = key[1:]

    consumption = expectation.get_mean_ttw_consumption(*vessel_key)
    slip = expectation.get_mean_ttw_slip(*vessel_key) if levy.include_slip else 0.0

    return consumption, slip


def _evaluate_supplied(
    policy: Levy | Regulation,
    supplied: dict[tuple[str, str], ForecastInput | None],
    times: FloatArray,
) -> dict[tuple[str, str], FloatArray | None]:
    """
    Evaluate a policy's supplied WTT or TTW of each targeted fuel and emission.

    A supplied factor is the same for every vessel and port, so it is evaluated once.

    Parameters
    ----------
    policy
        Policy whose supplied factors are evaluated.
    supplied
        Policy's `fuel_wtt` or `fuel_ttw`, keyed by fuel and emission name.
    times
        Remaining timeline, in days.

    Returns
    -------
    dict[tuple[str, str], FloatArray | None]
        Supplied factor over the remaining timeline, in ton emission/ton fuel, keyed by
        fuel and emission name; None where the policy supplies none.
    """
    evaluated = {}

    for fuel in policy.fuels:
        for emission in policy.emissions:
            key = (fuel.name, emission.name)
            factor = supplied[key]
            evaluated[key] = None if factor is None else factor.get(times)

    return evaluated


def _calculate_emission_factor(
    policy: Levy | Regulation,
    key_wtt: tuple[str, ...],
    key_ttw: tuple[str, ...],
    idx: int,
) -> FloatLike:
    """
    Calculate the emission factor from pre-defined WTT and TTW emission factors.

    Used for both levies and regulations.

    Parameters
    ----------
    policy
        Policy whose emission factor is calculated.
    key_wtt
        Key of the WTT factor in the policy's expectation.
    key_ttw
        Key of the TTW factors in the policy's expectation.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Emission factor from `idx` onward, in ton emission/ton fuel.
    """
    expectation = policy.expectation
    forward = np.s_[idx:]

    wtt = expectation.get_wtt(key_wtt, forward)
    ttw_consumption = expectation.get_ttw_consumption(key_ttw, forward)
    ttw_slip = expectation.get_ttw_slip(key_ttw, forward)

    # the WTT and TTW factors are adjusted for scope, slip and the like when they are
    # calculated, so the emission factor is their plain sum
    return wtt + ttw_consumption + ttw_slip


def _apply_gwp(
    emission_factor: FloatLike, policy: Levy | Regulation, emission: Emission
) -> FloatLike:
    """
    Convert an emission factor to CO2-equivalent units using the policy's GWP.

    Parameters
    ----------
    emission_factor
        Emission factor, in ton emission/ton fuel, or ton emission/GJ for shore power.
    policy
        Policy whose GWP weighs the factor.
    emission
        Emission whose GWP is applied.

    Returns
    -------
    FloatLike
        GWP-weighted emission factor, in the unit of `emission_factor`.
    """
    gwp = policy.expectation.get_global_warming_potential(emission.name)

    return emission_factor * gwp


def _target_fuels(policy: Levy | Regulation, vessel: Vessel) -> list[Fuel]:
    """
    Filter the policy's targeted fuels down to those usable by a vessel.

    Parameters
    ----------
    policy
        Policy whose targeted fuels are filtered.
    vessel
        Vessel whose usable fuels the targeted fuels are filtered by.

    Returns
    -------
    list[Fuel]
        Targeted fuels also usable by the vessel, in the policy's order.
    """
    return [fuel for fuel in policy.fuels if fuel.name in vessel.usable_fuels]


def _target_converter_fuels(
    regulation: Regulation, vessel: Vessel
) -> list[tuple[str, Fuel]]:
    """
    Pair each converter on board a vessel with each targeted fuel it burns.

    Parameters
    ----------
    regulation
        Regulation whose targeted fuels are paired.
    vessel
        Vessel whose converter-fuel pairs are read.

    Returns
    -------
    list[tuple[str, Fuel]]
        Each converter name with each targeted fuel it burns, converter by
        converter, the fuels in the regulation's order.
    """
    pairs = []

    for converter_name, burned in vessel.fuels_per_converter.items():
        for fuel in regulation.fuels:
            if fuel.name in burned:
                pairs.append((converter_name, fuel))

    return pairs


def _estimate_port_wtt(
    port: Port, fuel: Fuel, emission: Emission, plants: list[Plant], idx: int
) -> FloatLike:
    """
    Estimate the WTT emissions of a fuel bunkered at a port, from `idx` onward.

    The port's WTT overwrite takes precedence; a liquid-market fuel always has one, as
    the port fills in 0 where the deck sets none. Otherwise the estimate is the
    equal-weight mean, over every plant defined for the fuel, of the plant's
    production WTT at the time of investment plus its WTT of delivery to the port.
    The estimate reads no bunker supply, so it is known before the fuel import of the
    time step.

    A fuel no plant produces has no estimate, and the result is NaN: no port has
    supply of it, so no vessel can bunker it.

    Parameters
    ----------
    port
        Port at which the fuel's WTT emissions are estimated.
    fuel
        Fuel whose WTT emissions are estimated.
    emission
        Emission the estimate is for.
    plants
        Plants producing the fuel, whose production and delivery WTT are averaged.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        WTT emissions from `idx` onward, in ton emission/ton fuel.
    """
    forward = np.s_[idx:]
    key = (fuel.name, emission.name)

    if port.bunker_wtt_overwrite[key] is not None:
        return port.expectation.get_bunker_wtt_overwrite(*key, forward)

    if not plants:
        return np.full(port.expectation.get_shape(idx), np.nan)

    estimates = []
    for plant in plants:
        expectation = plant.expectation
        production = expectation.get_production_wtt(emission.name, forward)
        delivery = expectation.get_delivery_wtt(port.name, emission.name, forward)
        estimates.append(production + delivery)

    return np.stack(estimates).mean(axis=0)
