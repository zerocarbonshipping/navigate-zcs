# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Emission factors and coefficients of policies, regulation thresholds, levy costs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import LevySchemeID, PolicyScopeID, RegulationMeasureID
from navigate.util import (
    TON_PER_GJ_TO_GRAM_PR_MJ,
    TON_TO_KG,
    list_intersection,
    unique_list,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
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

    Combinations span regulations, levies, vessels, fuels, and emissions. The WTT and
    TTW emission factors can be used to calculate the overall emission factors, which
    are used in the calculation of the emission coefficients, which are used to
    convert a ton of fuel to a ton of emissions. A levy's coefficients, priced at
    its level, give its cost per ton of fuel. A regulation's coefficients, net of the
    vessel thresholds, give the spend coefficients its bunkering constraints weigh
    fuel and shore power with.

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
        Simulation timeline.
    idx
        Current time-step index.
    """
    plants_by_fuel = {
        fuel_name: [plant for plant in plants.values() if plant.fuel.name == fuel_name]
        for fuel_name in {plant.fuel.name for plant in plants.values()}
    }

    for regulation in regulations.values():
        if not regulation.is_active():
            continue

        _assign_regulation_emission_factors(
            regulation, vessels, plants_by_fuel, timeline, idx
        )

    for levy in levies.values():
        if not levy.is_active():
            continue

        _assign_levy_emission_factors(levy, vessels, plants_by_fuel, timeline, idx)


def _assign_regulation_emission_factors(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate and assign the WTT and TTW emission factors related to a regulation.

    From the factors follow the regulation's emission coefficients, and with its
    shore-power coefficients and vessel thresholds, the spend coefficients its
    bunkering constraints weigh.

    Parameters
    ----------
    regulation
        Regulation to calculate emission factor for.
    vessels
        All vessels in the simulation.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    scope = regulation.scope

    if scope in (PolicyScopeID.WTT, PolicyScopeID.WTW):
        _assign_regulation_wtt_factors(
            regulation, vessels, plants_by_fuel, timeline, idx
        )

    if scope in (PolicyScopeID.TTW, PolicyScopeID.WTW):
        _assign_regulation_ttw_factors(regulation, vessels, timeline, idx)

    _assign_regulation_emission_coefficients(regulation, vessels, idx)
    _calculate_regulation_shore_power_coefficients(regulation, vessels, idx)
    _calculate_regulation_vessel_thresholds(regulation, timeline, idx)
    _calculate_regulation_spend_coefficients(regulation, vessels, idx)


def _assign_regulation_wtt_factors(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate and assign the WTT emission factors related to a given regulation.

    Unless the regulation supplies a WTT, a vessel's factor is the mean of the port
    estimates over every port on its route, each counted once, as the vessel may
    bunker a fuel outside the jurisdiction and burn it inside. A fuel no route port
    has an estimate for gets a NaN factor.

    Parameters
    ----------
    regulation
        Regulation to calculate emission factor for.
    vessels
        All vessels in the simulation.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    fuel_wtts = regulation.fuel_wtt
    target_emissions = regulation.emissions

    # a supplied WTT is vessel-invariant, so it is evaluated once per (fuel, emission)
    times = timeline[idx:]
    supplied_wtts: dict[tuple[str, str], FloatArray | None] = {}
    for fuel in regulation.fuels:
        for emission in target_emissions:
            key = (fuel.name, emission.name)
            supplied = fuel_wtts[key]
            supplied_wtts[key] = None if supplied is None else supplied.get(times)

    for vessel_name, vessel in vessels.items():
        # a vessel with no route port in the jurisdiction is never policed (see
        # vessel_is_policed), so its factors would never be read
        if not regulation.in_jurisdiction_vessel[vessel_name]:
            continue

        ports = unique_list(vessel.route.ports)
        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(regulation, usable_fuels)

        for fuel in target_fuels:
            fuel_name = fuel.name
            fuel_plants = plants_by_fuel.get(fuel_name, [])

            for emission in target_emissions:
                emission_name = emission.name
                key = (fuel_name, emission_name)

                # user-supplied WTT overrides the route average
                supplied_wtt = supplied_wtts[key]
                wtt: FloatLike
                if supplied_wtt is not None:
                    wtt = supplied_wtt
                else:
                    wtt = _average_wtt_over_route(
                        ports, fuel, emission, fuel_plants, idx
                    )

                factor = _apply_gwp(wtt, regulation, emission)

                expectation.set_wtt(idx, (vessel_name, *key), factor)


def _assign_regulation_ttw_factors(
    regulation: Regulation, vessels: dict[str, Vessel], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate and assign the TTW emission factors related to a given regulation.

    Each converter able to burn a fuel on each vessel gets its own consumption and slip
    factors, read from the vessel's expectation unless the regulation supplies a TTW.

    Parameters
    ----------
    regulation
        Regulation to calculate emission factor for.
    vessels
        All vessels in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    fuel_ttws = regulation.fuel_ttw
    target_emissions = regulation.emissions

    # a supplied TTW is vessel-invariant, so it is evaluated once per (fuel, emission)
    times = timeline[idx:]
    supplied_ttws: dict[tuple[str, str], FloatArray | None] = {}
    for fuel in regulation.fuels:
        for emission in target_emissions:
            key = (fuel.name, emission.name)
            supplied = fuel_ttws[key]
            supplied_ttws[key] = None if supplied is None else supplied.get(times)

    for vessel_name, vessel in vessels.items():
        target_fuels = _usable_target_fuels(regulation, vessel.usable_fuels)

        for converter, fuel in _converter_fuels(vessel, target_fuels):
            for emission in target_emissions:
                supplied_ttw = supplied_ttws[(fuel.name, emission.name)]
                ttw_consumption, ttw_slip = _regulation_ttw(
                    regulation, vessel, converter, fuel, emission, supplied_ttw
                )

                factor_consumption = _apply_gwp(ttw_consumption, regulation, emission)
                factor_slip = _apply_gwp(ttw_slip, regulation, emission)

                key = (vessel_name, converter.name, fuel.name, emission.name)
                expectation.set_ttw_consumption(idx, key, factor_consumption)
                expectation.set_ttw_slip(idx, key, factor_slip)


def _assign_regulation_emission_coefficients(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    idx: int,
) -> None:
    """
    Calculate and assign the emission coefficients related to a given regulation.

    Parameters
    ----------
    regulation
        Regulation to calculate emission coefficients for.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    target_emissions = regulation.emissions

    for vessel_name, vessel in vessels.items():
        target_fuels = _usable_target_fuels(regulation, vessel.usable_fuels)

        for converter, fuel in _converter_fuels(vessel, target_fuels):
            coefficient: FloatLike = 0.0
            for emission in target_emissions:
                coefficient += _calculate_regulation_emission_factor(
                    regulation, vessel, converter, fuel, emission, idx
                )

            # a NaN WTT factor, as where no route port has an estimate for the
            # fuel, leaves the fuel without a coefficient, its TTW part included;
            # without an estimate no route port supplies the fuel, so the LP
            # spends none of it, and the missing coefficient reads as zero
            if np.isnan(coefficient).any():
                continue

            key = (vessel_name, converter.name, fuel.name)

            regulation.expectation.set_emission_coefficient(idx, key, coefficient)


def _calculate_regulation_emission_factor(
    regulation: Regulation,
    vessel: Vessel,
    converter: Converter,
    fuel: Fuel,
    emission: Emission,
    idx: int,
) -> FloatLike:
    """
    Calculate the emission factor, in ton emissions per ton fuel, for one emission.

    Used in the calculation of a regulation emission coefficient.

    Parameters
    ----------
    regulation
        Regulation to calculate emission factor for.
    vessel
        Vessel impacted by the regulation.
    converter
        Converter on board the vessel.
    fuel
        Fuel with certain emissions impacted by the regulation.
    emission
        Emission for which the emission factor is calculated.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Emission factor, in ton emissions per ton fuel.
    """
    vessel_name = vessel.name
    converter_name = converter.name
    fuel_name = fuel.name
    emission_name = emission.name

    key_wtt = (vessel_name, fuel_name, emission_name)
    key_ttw = (vessel_name, converter_name, fuel_name, emission_name)

    return _calculate_emission_factor(regulation, key_wtt, key_ttw, idx)


def _calculate_regulation_shore_power_coefficients(
    regulation: Regulation, vessels: dict[str, Vessel], idx: int
) -> None:
    """
    Calculate the regulation's shore-power emission coefficient at each route port.

    Parameters
    ----------
    regulation
        Regulation to calculate the coefficients for.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    from_idx = np.s_[idx:]

    route_ports = (port for vessel in vessels.values() for port in vessel.route.ports)

    for port in unique_list(route_ports):
        get_emission_factor = port.expectation.get_shore_power_emission_factor

        coefficient: FloatLike = 0.0
        for emission in regulation.emissions:
            factor = get_emission_factor(emission.name, from_idx)
            coefficient += _apply_gwp(factor, regulation, emission)

        expectation.set_shore_power_emission_coefficient(idx, port.name, coefficient)


def _calculate_regulation_vessel_thresholds(
    regulation: Regulation, timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the threshold each vessel must satisfy, zero where it is not policed.

    Parameters
    ----------
    regulation
        Regulation to calculate the thresholds for.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    times = timeline[idx:]

    for vessel_name, threshold in regulation.vessel_threshold.items():
        # zero rather than unwritten: an event can stop the regulation policing the
        # vessel, and the threshold written while it did would remain;
        # check_consistency guarantees every policed vessel a threshold
        if not regulation.vessel_is_policed(vessel_name) or threshold is None:
            expectation.set_vessel_threshold(idx, vessel_name, 0.0)
            continue

        expectation.set_vessel_threshold(idx, vessel_name, threshold.get(times))


def _calculate_regulation_spend_coefficients(
    regulation: Regulation, vessels: dict[str, Vessel], idx: int
) -> None:
    """
    Calculate the spend coefficients the regulation's bunkering constraints weigh.

    Under an INTENSITY measure, a spend coefficient is the emission coefficient net of
    the vessel's threshold, converted from kg emission/GJ by the effective LHV, so the
    constraint compares the weighted spend with zero; shore power is in GJ, so its
    effective LHV is 1. Under any other measure the threshold enters the right-hand
    side instead, and the spend coefficient is the emission coefficient. Every fuel a
    converter can burn gets one, as the constraints weigh all spend: an untargeted
    fuel, without an emission coefficient, nets out the threshold alone.

    Parameters
    ----------
    regulation
        Regulation to calculate the spend coefficients for.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    expectation = regulation.expectation
    from_idx = np.s_[idx:]
    is_intensity = regulation.measure == RegulationMeasureID.INTENSITY

    get_shore_power_emission = expectation.get_shore_power_emission_coefficient

    for vessel_name, vessel in vessels.items():
        vessel_expectation = vessel.expectation
        usable_fuels = vessel.usable_fuels.values()
        threshold = expectation.get_vessel_threshold(vessel_name, from_idx)

        # in ton emission/GJ; zero where the threshold enters the right-hand side
        threshold_term = threshold / TON_TO_KG if is_intensity else 0.0

        for converter, fuel in _converter_fuels(vessel, usable_fuels):
            fuel_key = (vessel_name, converter.name, fuel.name)
            lhv = vessel_expectation.get_effective_lhv(converter.name, fuel.name)
            emission = expectation.get_emission_coefficient(fuel_key, from_idx)

            spend = emission - threshold_term * lhv
            expectation.set_spend_coefficient(idx, fuel_key, spend)

        for port in unique_list(vessel.route.ports):
            port_key = (vessel_name, port.name)
            emission = get_shore_power_emission(port.name, from_idx)

            spend = emission - threshold_term
            expectation.set_shore_power_spend_coefficient(idx, port_key, spend)


def _assign_levy_emission_factors(
    levy: Levy,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate and assign the WTT and TTW emission factors of a levy, and its costs.

    Parameters
    ----------
    levy
        Levy to calculate emission factor for.
    vessels
        All vessels in the simulation.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    scope = levy.scope

    if scope in (PolicyScopeID.WTT, PolicyScopeID.WTW):
        _assign_levy_wtt_factors(levy, plants_by_fuel, timeline, idx)

    if scope in (PolicyScopeID.TTW, PolicyScopeID.WTW):
        _assign_levy_ttw_factors(levy, vessels, timeline, idx)

    _calculate_levy_costs(levy, vessels, timeline, idx)


def _assign_levy_wtt_factors(
    levy: Levy,
    plants_by_fuel: dict[str, list[Plant]],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate and assign the WTT emission factor related to a given levy.

    Unless the levy supplies a WTT, the factor at each jurisdiction port is the port
    estimate. A port that disallows bunkering the fuel gets a NaN factor, as does a
    port without an estimate for it.

    Parameters
    ----------
    levy
        Levy to calculate emission factor for.
    plants_by_fuel
        Plants producing each fuel, keyed by fuel name; a fuel no plant produces is
        absent.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    expectation = levy.expectation
    fuel_wtts = levy.fuel_wtt
    target_emissions = levy.emissions

    for fuel in levy.fuels:
        fuel_name = fuel.name
        fuel_plants = plants_by_fuel.get(fuel_name, [])

        for emission in target_emissions:
            emission_name = emission.name

            # user-supplied WTT (None falls back to the port estimate resolved
            # inside the per-port loop below).
            key = (fuel_name, emission_name)
            supplied = fuel_wtts[key]
            wtt_supplied = (
                supplied.get(timeline[idx:]) if supplied is not None else None
            )

            for port in levy.jurisdiction:
                port_name = port.name

                factor: FloatLike
                if not port.is_bunkering_allowed(fuel_name):
                    factor = np.nan
                else:
                    wtt: FloatLike
                    if wtt_supplied is not None:
                        wtt = wtt_supplied
                    else:
                        wtt = _estimate_port_wtt(port, fuel, emission, fuel_plants, idx)

                    factor = _apply_gwp(wtt, levy, emission)

                expectation.set_wtt(idx, (port_name, *key), factor)


def _assign_levy_ttw_factors(
    levy: Levy, vessels: dict[str, Vessel], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate and assign the TTW emission factors related to a given levy.

    Parameters
    ----------
    levy
        Levy to calculate emission factor for.
    vessels
        All vessels in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    expectation = levy.expectation
    fuel_ttws = levy.fuel_ttw
    target_emissions = levy.emissions

    for vessel_name, vessel in vessels.items():
        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(levy, usable_fuels)

        for fuel in target_fuels:
            fuel_name = fuel.name

            for emission in target_emissions:
                emission_name = emission.name

                key = (vessel_name, fuel_name, emission_name)
                ttw = fuel_ttws[(fuel_name, emission_name)]

                if ttw is not None:
                    # user-supplied TTW applies uniformly with zero slip
                    ttw_consumption = ttw.get(timeline[idx:])
                    ttw_slip = 0.0  # TODO: change if deciding to split input
                else:
                    ttw_consumption, ttw_slip = _mean_ttw(levy, vessel, fuel, emission)

                factor_consumption = _apply_gwp(ttw_consumption, levy, emission)
                factor_slip = _apply_gwp(ttw_slip, levy, emission)

                expectation.set_ttw_consumption(idx, key, factor_consumption)
                expectation.set_ttw_slip(idx, key, factor_slip)


def _calculate_levy_costs(
    levy: Levy, vessels: dict[str, Vessel], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate the levy's cost per ton of each fuel a vessel bunkers in its ports.

    The cost is the levy's level times the fuel's threshold-adjusted emission
    coefficient, from the current time step onward, and zero for a vessel the levy
    does not police.

    Parameters
    ----------
    levy
        Levy to calculate costs for.
    vessels
        All vessels in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    expectation = levy.expectation
    upper = levy.upper_threshold
    times = timeline[idx:]

    # the level and thresholds are levy-wide, not vessel/port/fuel-specific, so
    # they are read once per pass rather than inside the loops below
    level = expectation.get_level(np.s_[idx:])
    lower_threshold = levy.lower_threshold.get(times)
    upper_threshold = None if upper is None else upper.get(times)

    for vessel_name, vessel in vessels.items():
        ports = list_intersection(vessel.route.ports, levy.jurisdiction)
        if not ports:
            continue

        policed = levy.vessel_is_policed(vessel_name)
        target_fuels = _usable_target_fuels(levy, vessel.usable_fuels)

        for fuel in target_fuels:
            lhv = vessel.expectation.get_mean_effective_lhv(fuel.name)

            for port in ports:
                if not port.is_bunkering_allowed(fuel.name):
                    continue

                key = (vessel_name, port.name, fuel.name)

                # zero rather than unwritten: an event can stop the levy policing
                # the vessel, and the cost written while it did would remain
                if not policed:
                    expectation.set_cost(idx, key, 0.0)
                    continue

                coefficient = _calculate_levy_coefficient(levy, vessel, port, fuel, idx)

                # a NaN WTT factor, as where the port has no estimate for the fuel,
                # makes the whole coefficient NaN, TTW part included, so the fuel
                # gets no cost at the port; without an estimate the port has no
                # supply of the fuel, so the LP bunkers none of it there and reads
                # the missing cost as zero
                if np.isnan(coefficient).any():
                    continue

                coefficient = _calculate_threshold_adjusted_levy_emission_coefficient(
                    coefficient, levy, lhv, lower_threshold, upper_threshold
                )

                expectation.set_cost(idx, key, level * coefficient)


def _calculate_levy_coefficient(
    levy: Levy, vessel: Vessel, port: Port, fuel: Fuel, idx: int
) -> FloatLike:
    """
    Calculate the levy's emission coefficient of a fuel a vessel bunkers at a port.

    The coefficient sums, over the levy's emissions, the fuel's WTT factor at the
    port and its TTW factors on the vessel.

    Parameters
    ----------
    levy
        Levy to calculate the emission coefficient for.
    vessel
        Vessel impacted by the levy.
    port
        Port in which the fuel is bunkered.
    fuel
        Fuel with certain emissions impacted by the levy.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Emission coefficient, in ton emissions per ton fuel, from idx onward.
    """
    coefficient: FloatLike = 0.0

    for emission in levy.emissions:
        key_wtt = (port.name, fuel.name, emission.name)
        key_ttw = (vessel.name, fuel.name, emission.name)
        coefficient += _calculate_emission_factor(levy, key_wtt, key_ttw, idx)

    return coefficient


def _calculate_threshold_adjusted_levy_emission_coefficient(
    coefficient: FloatLike,
    levy: Levy,
    effective_lhv: FloatLike,
    lower_threshold: FloatArray,
    upper_threshold: FloatArray | None,
) -> FloatLike:
    """
    Calculate the threshold adjusted levy emission coefficient.

    The thresholds are intensities per GJ of effective energy, (1 - slip) * LHV, and
    are converted to ton emission/ton fuel on that basis before they are applied. A
    fuel whose converters slip all of it delivers no energy, so its thresholds are
    zero and its whole coefficient is levied.

    Parameters
    ----------
    coefficient
        Emission coefficient in ton emission/ton fuel.
    levy
        Levy to calculate emission coefficient for.
    effective_lhv
        Effective lower heating value of the fuel on the vessel, in GJ/ton fuel.
    lower_threshold
        Lower emission factor threshold, evaluated from the current time-step onward,
        in kg emissions/GJ.
    upper_threshold
        Upper emission factor threshold, evaluated from the current time-step onward,
        in kg emissions/GJ; None where the levy has no upper threshold.

    Returns
    -------
    FloatLike
        The reference adjusted emission coefficient in ton emission/ton fuel.
    """
    scheme = levy.scheme

    intensity_to_coefficient = effective_lhv / TON_PER_GJ_TO_GRAM_PR_MJ

    coefficient_ref = coefficient - lower_threshold * intensity_to_coefficient

    if scheme == LevySchemeID.PENALTY:
        coefficient_ref = np.maximum(coefficient_ref, 0.0)
    elif scheme == LevySchemeID.SUBSIDY:
        coefficient_ref = np.minimum(coefficient_ref, 0.0)

    if scheme != LevySchemeID.SUBSIDY and upper_threshold is not None:
        coefficient_ref = np.minimum(
            coefficient_ref,
            (upper_threshold - lower_threshold) * intensity_to_coefficient,
        )

    return coefficient_ref


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
        Ports on the vessel's route, each listed once.
    fuel
        Fuel being spent.
    emission
        Emission.
    plants
        Plants producing the fuel.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        Approximate WTT from `idx` onward, in ton emission/ton fuel.
    """
    fuel_name = fuel.name

    estimates: list[FloatLike] = []
    for port in ports:
        if not port.is_bunkering_allowed(fuel_name):
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


def _regulation_ttw(
    regulation: Regulation,
    vessel: Vessel,
    converter: Converter,
    fuel: Fuel,
    emission: Emission,
    supplied_ttw: FloatArray | None,
) -> tuple[FloatLike, FloatLike]:
    """
    Return the consumption and slip TTW of burning a fuel in a vessel's converter.

    A TTW supplied on the regulation applies to every converter able to burn the fuel,
    with zero slip.

    Parameters
    ----------
    regulation
        Regulation the TTW is read for; where it leaves out slip, the slip TTW is zero.
    vessel
        Vessel the converter is on board.
    converter
        Converter able to burn the fuel.
    fuel
        Fuel being spent.
    emission
        Emission.
    supplied_ttw
        TTW the regulation supplies for the fuel and emission, if any.

    Returns
    -------
    tuple[FloatLike, FloatLike]
        Consumption TTW and slip TTW, in ton emission/ton fuel-in.
    """
    if supplied_ttw is not None:
        return supplied_ttw, 0.0  # TODO: change if deciding to split input

    key = (converter.name, fuel.name, emission.name)
    expectation = vessel.expectation

    ttw_consumption = expectation.get_ttw_consumption(*key)
    ttw_slip = expectation.get_ttw_slip(*key) if regulation.include_slip else 0.0

    return ttw_consumption, ttw_slip


def _mean_ttw(
    levy: Levy, vessel: Vessel, fuel: Fuel, emission: Emission
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
        Vessel on which the fuel is spent.
    fuel
        Fuel being spent.
    emission
        Emission.

    Returns
    -------
    tuple[float, float]
        Consumption TTW and slip TTW, in ton emission/ton fuel-in.
    """
    key = (fuel.name, emission.name)
    expectation = vessel.expectation

    ttw_consumption = expectation.get_mean_ttw_consumption(*key)
    ttw_slip = expectation.get_mean_ttw_slip(*key) if levy.include_slip else 0.0

    return ttw_consumption, ttw_slip


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
        The Levy or Regulation being calculated.
    key_wtt
        The key to the WTT attribute of the policy profile.
    key_ttw
        The key to the TTW attributes of the policy profile.
    idx
        Time-step index.

    Returns
    -------
    FloatLike
        Emission factor, in ton emissions per ton fuel.
    """
    from_idx = np.s_[idx:]

    expectation = policy.expectation

    wtt = expectation.get_wtt(key_wtt, from_idx)
    ttw_consumption = expectation.get_ttw_consumption(key_ttw, from_idx)
    ttw_slip = expectation.get_ttw_slip(key_ttw, from_idx)

    # during calculation of the WTT and TTWs
    # results are adjusted for scope, inclusion
    # of slip, etc. so that reconstruction of the
    # emission factor can be made without checks
    return wtt + ttw_consumption + ttw_slip


def _apply_gwp(
    emission_factor: FloatLike, policy: Levy | Regulation, emission: Emission
) -> FloatLike:
    """
    Convert an emission factor to CO2-equivalent units using the policy's GWP.

    Parameters
    ----------
    emission_factor
        Emission factor.
    policy
        The policy whose expectation supplies the GWP.
    emission
        Emission being converted.

    Returns
    -------
    FloatLike
        GWP-weighted emission factor.
    """
    gwp = policy.expectation.get_global_warming_potential(emission.name)

    return emission_factor * gwp


def _usable_target_fuels(
    policy: Levy | Regulation, usable_fuels: dict[str, Fuel]
) -> list[Fuel]:
    """
    Filter the policy's targeted fuels down to those usable by a vessel's power system.

    Parameters
    ----------
    policy
        The policy whose targeted fuels are filtered.
    usable_fuels
        Fuels usable by the vessel's power system, keyed by name.

    Returns
    -------
    list[Fuel]
        Targeted fuels also usable by the vessel.
    """
    return [fuel for fuel in policy.fuels if fuel.name in usable_fuels]


def _converter_fuels(
    vessel: Vessel, fuels: Collection[Fuel]
) -> list[tuple[Converter, Fuel]]:
    """
    Pair each converter on board a vessel with each of the fuels it can burn.

    Parameters
    ----------
    vessel
        Vessel whose converters are paired.
    fuels
        Fuels to pair the converters with.

    Returns
    -------
    list[tuple[Converter, Fuel]]
        Every converter with every fuel of `fuels` it can burn, converter by
        converter.
    """
    pairs: list[tuple[Converter, Fuel]] = []

    for converter in vessel.power_system.get_converters():
        fuel_types = converter.get_fuel_types()

        for fuel in fuels:
            if fuel.fuel_type in fuel_types:
                pairs.append((converter, fuel))

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
        Port at which the fuel is bunkered.
    fuel
        Fuel being bunkered.
    emission
        Emission.
    plants
        Plants producing the fuel.
    idx
        Current time-step index.

    Returns
    -------
    FloatLike
        WTT emissions from `idx` onward, in ton emission/ton fuel.
    """
    from_idx = np.s_[idx:]

    port_name = port.name
    fuel_name = fuel.name
    emission_name = emission.name

    if port.bunker_wtt_overwrite[(fuel_name, emission_name)] is not None:
        return port.expectation.get_bunker_wtt_overwrite(
            fuel_name, emission_name, from_idx
        )

    if not plants:
        return np.full(port.expectation.get_shape(idx), np.nan)

    estimates = [
        plant.expectation.get_production_wtt(emission_name, from_idx)
        + plant.expectation.get_delivery_wtt(port_name, emission_name, from_idx)
        for plant in plants
    ]

    return np.stack(estimates).mean(axis=0)
