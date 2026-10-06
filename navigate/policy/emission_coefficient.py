# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
WTT, TTW and overall emission coefficients of regulations and levies.

The default WTT of a fuel bunkered at a port is estimated from the plants producing
the fuel and reads no bunker supply, so the coefficients are calculated once per time
step, before either bunkering run.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import LevySchemeID, PolicyScopeID
from navigate.core.unit import TON_PER_GJ_TO_GRAM_PR_MJ
from navigate.util import divide_nonzero, list_intersection, unique_list

if TYPE_CHECKING:
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
    Calculate WTT and TTW emission factors for each combination of inputs.

    Combinations span regulations, levies, vessels, fuels, and emissions. The WTT and
    TTW emission factors can be used to calculate the overall emission factors, which
    are used in the calculation of the emission coefficients, which are used to
    converter a ton of fuel to a ton of emissions.

    Reads the plants' production and delivery WTT of the current time step, so it runs
    after those are calculated.

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

    # precompute user-supplied WTT once per (fuel, emission); these are
    # vessel-invariant, so evaluating them inside the vessel loop is wasted work.
    wtt_supplied: dict[tuple[str, str], FloatArray | None] = {}
    for fuel in regulation.fuels:
        for emission in target_emissions:
            key = (fuel.name, emission.name)
            supplied = fuel_wtts[key]
            wtt_supplied[key] = (
                supplied.get(timeline[idx:]) if supplied is not None else None
            )

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
                supplied_wtt = wtt_supplied[key]
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
    include_slip = regulation.include_slip

    expectation = regulation.expectation
    fuel_ttws = regulation.fuel_ttw
    target_emissions = regulation.emissions

    for vessel in vessels.values():
        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(regulation, usable_fuels)

        converters = vessel.power_system.get_converters()

        for fuel in target_fuels:
            fuel_name = fuel.name

            for emission in target_emissions:
                emission_name = emission.name

                # if a user-supplied TTW is assigned on the regulation, it
                # applies uniformly to every converter (with zero slip);
                # otherwise the model derives a converter-specific value
                key = (fuel_name, emission_name)
                ttw = fuel_ttws[key]
                ttw_supplied = ttw.get(timeline[idx:]) if ttw is not None else None

                for converter in converters:
                    converter_name = converter.name

                    ttw_consumption: FloatLike
                    if ttw_supplied is not None:
                        ttw_consumption = ttw_supplied
                        ttw_slip = 0.0  # TODO: change if deciding to split input
                    else:
                        ttw_consumption, ttw_slip = _calculate_converter_ttw(
                            converter, fuel, emission, include_slip
                        )

                    factor_consumption = _apply_gwp(
                        ttw_consumption, regulation, emission
                    )
                    factor_slip = _apply_gwp(ttw_slip, regulation, emission)

                    expectation.set_ttw_consumption(
                        idx, (converter_name, *key), factor_consumption
                    )
                    expectation.set_ttw_slip(idx, (converter_name, *key), factor_slip)


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
        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(regulation, usable_fuels)

        for converter in vessel.power_system.get_converters():
            converter_name = converter.name
            fuel_types = converter.get_fuel_types()

            for fuel in target_fuels:
                fuel_name = fuel.name

                if fuel.fuel_type not in fuel_types:
                    continue

                coefficient: FloatLike = 0.0
                for emission in target_emissions:
                    coefficient += _calculate_regulation_emission_factor(
                        regulation, vessel, converter, fuel, emission, idx
                    )

                # a NaN WTT factor, as where no route port has an estimate for the
                # fuel, leaves the fuel without a coefficient, its TTW part
                # included; without an estimate no route port supplies the fuel,
                # so the LP spends none of it and reads the missing coefficient
                # as zero
                if np.isnan(coefficient).any():
                    continue

                key = (vessel_name, converter_name, fuel_name)

                regulation.expectation.set_coefficient(idx, key, coefficient)


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
    key_ttw = (converter_name, fuel_name, emission_name)

    return _calculate_emission_factor(regulation, key_wtt, key_ttw, idx)


def _assign_levy_emission_factors(
    levy: Levy,
    vessels: dict[str, Vessel],
    plants_by_fuel: dict[str, list[Plant]],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate and assign the WTT and TTW emission factors related to a given levy.

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

    _assign_levy_emission_coefficients(levy, vessels, timeline, idx)


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
    include_slip = levy.include_slip

    expectation = levy.expectation
    fuel_ttws = levy.fuel_ttw
    target_emissions = levy.emissions

    for vessel_name, vessel in vessels.items():
        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(levy, usable_fuels)

        for fuel in target_fuels:
            fuel_name = fuel.name
            weights = _converter_weights(vessel, fuel)

            for emission in target_emissions:
                emission_name = emission.name

                key = (vessel_name, fuel_name, emission_name)
                ttw = fuel_ttws[(fuel_name, emission_name)]

                ttw_slip: FloatLike
                if ttw is not None:
                    # user-supplied TTW applies uniformly with zero slip
                    ttw_consumption = ttw.get(timeline[idx:])
                    ttw_slip = 0.0  # TODO: change if deciding to split input
                else:
                    # otherwise approximate as a power/efficiency weighted average
                    # across the converters in the vessel's power system
                    ttw_consumption, ttw_slip = _average_ttw_over_converters(
                        weights, fuel, emission, include_slip
                    )

                factor_consumption = _apply_gwp(ttw_consumption, levy, emission)
                factor_slip = _apply_gwp(ttw_slip, levy, emission)

                expectation.set_ttw_consumption(idx, key, factor_consumption)
                expectation.set_ttw_slip(idx, key, factor_slip)


def _assign_levy_emission_coefficients(
    levy: Levy,
    vessels: dict[str, Vessel],
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate and assign the emission coefficients related to a given levy.

    Parameters
    ----------
    levy
        Levy to calculate emission coefficients for.
    vessels
        All vessels in the simulation.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """
    target_emissions = levy.emissions

    # thresholds are levy-wide, not vessel/port/fuel-specific, so they are
    # evaluated once per pass rather than inside the loops below
    lower_threshold = levy.lower_threshold.get(timeline[idx:])
    upper_threshold_obj = levy.upper_threshold
    upper_threshold = (
        upper_threshold_obj.get(timeline[idx:])
        if upper_threshold_obj is not None
        else None
    )

    for vessel_name, vessel in vessels.items():
        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(levy, usable_fuels)

        ports = list_intersection(vessel.route.ports, levy.jurisdiction)
        if not ports:
            continue

        effective_lhvs = {
            fuel.name: _average_effective_lhv_over_converters(
                _converter_weights(vessel, fuel), fuel
            )
            for fuel in target_fuels
        }

        for port in ports:
            port_name = port.name

            for fuel in target_fuels:
                fuel_name = fuel.name

                if not port.is_bunkering_allowed(fuel_name):
                    continue

                coefficient: FloatLike = 0.0
                for emission in target_emissions:
                    coefficient += _calculate_levy_emission_factor(
                        levy, vessel, port, fuel, emission, idx
                    )

                # a NaN WTT factor, as where the port has no estimate for the fuel,
                # leaves the fuel without a coefficient at the port, its TTW part
                # included; without an estimate the port has no supply of the
                # fuel, so the LP bunkers none of it there and reads the missing
                # coefficient as zero
                if np.isnan(coefficient).any():
                    continue

                coefficient = _calculate_threshold_adjusted_levy_emission_coefficient(
                    coefficient,
                    levy,
                    effective_lhvs[fuel_name],
                    lower_threshold,
                    upper_threshold,
                )

                key = (vessel_name, port_name, fuel_name)

                levy.expectation.set_coefficient(idx, key, coefficient)


def _calculate_levy_emission_factor(
    levy: Levy,
    vessel: Vessel,
    port: Port,
    fuel: Fuel,
    emission: Emission,
    idx: int,
) -> FloatLike:
    """
    Calculate the emission factor, in ton emissions per ton fuel, for one emission.

    Used in the calculation of a levy emission coefficient.

    Parameters
    ----------
    levy
        Levy to calculate emission factor for.
    vessel
        Vessel impacted by the levy.
    port
        Port in which the fuel was produced.
    fuel
        Fuel with certain emissions impacted by the levy.
    emission
        Emission for which the emission factor is calculated.
    idx
        Time-step index.

    Returns
    -------
    FloatLike
        Emission factor, in ton emissions per ton fuel.
    """
    vessel_name = vessel.name
    port_name = port.name
    fuel_name = fuel.name
    emission_name = emission.name

    key_wtt = (port_name, fuel_name, emission_name)
    key_ttw = (vessel_name, fuel_name, emission_name)

    return _calculate_emission_factor(levy, key_wtt, key_ttw, idx)


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


def _calculate_converter_ttw(
    converter: Converter, fuel: Fuel, emission: Emission, include_slip: bool
) -> tuple[float, float]:
    """
    Calculate the TTW emission factor for a specific converter.

    Parameters
    ----------
    converter
        The converter for which the TTW is calculated.
    fuel
        The fuel for which the TTW is calculated.
    emission
        The emission for which the TTW is calculated.
    include_slip
        Whether to include gas slip or not.

    Returns
    -------
    tuple[float, float]
        Consumption TTW and slip TTW.
    """
    emission_name = emission.name
    fuel_type = fuel.fuel_type

    if fuel_type not in converter.get_fuel_types():
        return 0.0, 0.0

    slip = converter.slip_fraction[fuel_type].get()

    # fuel-bound TTW emissions scale with burned fraction (1 - slip)
    ttw_consumption = (1.0 - slip) * fuel.ttw[emission_name].get()

    # consumption emissions per ton fuel-in, no slip scaling
    ttw_consumption += converter.consumption_ttw[(fuel_type, emission_name)].get()

    # slip emissions: X per ton fuel-in, gated by emission fuel_type
    ttw_slip = 0.0
    if include_slip:
        emission_fuel_type = emission.fuel_type
        if emission_fuel_type == fuel_type:
            ttw_slip = slip

    return ttw_consumption, ttw_slip


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


def _converter_weights(vessel: Vessel, fuel: Fuel) -> list[tuple[Converter, float]]:
    """
    Weigh the vessel's converters that can burn a fuel by power over efficiency.

    Converters that cannot burn the fuel are left out, so they carry no weight in an
    average over the weights. A converter with zero efficiency delivers no energy and
    so burns no fuel; it weighs zero.

    Parameters
    ----------
    vessel
        Vessel on which the fuel is spent.
    fuel
        Fuel being spent.

    Returns
    -------
    list[tuple[Converter, float]]
        Each converter able to burn the fuel with its weight, in MW.
    """
    fuel_type = fuel.fuel_type

    weights: list[tuple[Converter, float]] = []
    for converter in vessel.power_system.get_converters():
        if fuel_type not in converter.get_fuel_types():
            continue

        power = converter.power_capacity.get()
        efficiency = converter.efficiency.get()
        weight = power / efficiency if efficiency > 0.0 else 0.0

        weights.append((converter, weight))

    return weights


def _average_ttw_over_converters(
    weights: list[tuple[Converter, float]],
    fuel: Fuel,
    emission: Emission,
    include_slip: bool,
) -> tuple[FloatArray, FloatArray]:
    """
    Estimate a vessel's TTW emissions as a power/efficiency weighted average.

    Averaged over the converters in the vessel's power system that can burn the fuel.

    Parameters
    ----------
    weights
        Converters able to burn the fuel with their weights, from `_converter_weights`.
    fuel
        Fuel being spent.
    emission
        Emission.
    include_slip
        Whether slip is included in the calculation of the levy TTW.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Approximate consumption TTW and slip TTW of the vessel.
    """
    weighted_consumption_sum = 0.0
    weighted_slip_sum = 0.0
    weight_total = 0.0

    for converter, weight in weights:
        consumption, slip = _calculate_converter_ttw(
            converter, fuel, emission, include_slip
        )

        weighted_consumption_sum += weight * consumption
        weighted_slip_sum += weight * slip
        weight_total += weight

    ttw_consumption = divide_nonzero(weighted_consumption_sum, weight_total)
    ttw_slip = divide_nonzero(weighted_slip_sum, weight_total)

    return ttw_consumption, ttw_slip


def _average_effective_lhv_over_converters(
    weights: list[tuple[Converter, float]], fuel: Fuel
) -> FloatArray:
    """
    Estimate a vessel's effective LHV of a fuel as a power/efficiency weighted average.

    A vessel without weight on any converter able to burn the fuel has no slip to net
    off, so it falls back to the fuel's LHV.

    Parameters
    ----------
    weights
        Converters able to burn the fuel with their weights, from `_converter_weights`.
    fuel
        Fuel being spent.

    Returns
    -------
    FloatArray
        Effective lower heating value, (1 - slip) * LHV, in GJ/ton fuel.
    """
    weighted_lhv_sum = 0.0
    weight_total = 0.0

    for converter, weight in weights:
        weighted_lhv_sum += weight * converter.get_effective_lhv(fuel)
        weight_total += weight

    return divide_nonzero(
        weighted_lhv_sum, weight_total, default=fuel.lower_heating_value.get()
    )


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
    factor = wtt + ttw_consumption + ttw_slip

    return factor


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
