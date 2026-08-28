# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID, LevySchemeID, PolicyScopeID
from navigate.core.unit import TON_PER_GJ_TO_GRAM_PR_MJ
from navigate.util import TOLERANCE, divide_nonzero, list_intersection

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel


def calculate_policy_emission_coefficients(regulations: dict[str, Regulation],
                                           levies: dict[str, Levy],
                                           vessels: dict[str, Vessel],
                                           bunker_scope: BunkerScopeID,
                                           timeline: np.ndarray,
                                           idx: int) -> None:
    """
    Calculate WTT and TTW emission factors for all combinations of regulations, levies, vessels, fuels and emissions.
    The WTT and TTW emission factors can be used to calculate the overall emission factors which are used in the
    calculation of the emission coefficients which are used to converter a ton of fuel to a ton of emissions.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    levies
        All levies in the simulation.
    vessels
        All vessels in the simulation.
    bunker_scope
        ID of the bunker scope.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """

    for regulation in regulations.values():

        if not regulation.is_active():
            continue

        _assign_regulation_emission_factors(regulation, vessels, bunker_scope, timeline, idx)

    for levy in levies.values():

        if not levy.is_active():
            continue

        _assign_levy_emission_factors(levy, vessels, bunker_scope, timeline, idx)


def _assign_regulation_emission_factors(regulation: Regulation,
                                        vessels: dict[str, Vessel],
                                        bunker_scope: BunkerScopeID,
                                        timeline: np.ndarray,
                                        idx: int) -> None:
    """
    Calculates and assigns the WTT and TTW emission factors related to a given regulation.

    Parameters
    ----------
    regulation
        Regulation to calculate emission factor for.
    vessels
        All vessels in the simulation.
    bunker_scope
        ID of the bunker scope.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """

    scope = regulation.scope

    if scope in (PolicyScopeID.WTT, PolicyScopeID.WTW):
        _assign_regulation_wtt_factors(regulation, vessels, bunker_scope, timeline, idx)

    if scope in (PolicyScopeID.TTW, PolicyScopeID.WTW):
        _assign_regulation_ttw_factors(regulation, vessels, timeline, idx)

    _assign_regulation_emission_coefficients(regulation, vessels, bunker_scope, idx)


def _assign_regulation_wtt_factors(regulation: Regulation,
                                   vessels: dict[str, Vessel],
                                   bunker_scope: BunkerScopeID,
                                   timeline: np.ndarray,
                                   idx: int) -> None:
    """
    Calculates and assigns the WTT emission factors related to a given regulation.

    Parameters
    ----------
    regulation
        Regulation to calculate emission factor for.
    vessels
        All vessels in the simulation.
    bunker_scope
        ID of the bunker scope.
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
    wtt_supplied = {}
    for fuel in regulation.fuels:
        for emission in target_emissions:
            key = (fuel.name, emission.name)
            supplied = fuel_wtts[key]
            wtt_supplied[key] = supplied.get(timeline[idx:]) if supplied is not None else None

    for vessel_name, vessel in vessels.items():

        # find the ports that overlap between the
        # vessel route and the regulation jurisdiction
        ports = list_intersection(vessel.route.ports, regulation.jurisdiction)

        # the vessel does not operate in
        # the jurisdiction of the regulation
        if not ports:
            continue

        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(regulation, usable_fuels)

        for fuel in target_fuels:
            fuel_name = fuel.name

            for emission in target_emissions:
                emission_name = emission.name
                key = (fuel_name, emission_name)

                # user-supplied WTT overrides the per-port average
                if wtt_supplied[key] is not None:
                    factor = wtt_supplied[key]
                else:
                    factor = _average_wtt_over_ports(ports, fuel, emission, idx)

                factor = _apply_gwp(factor, regulation, emission)

                if bunker_scope == BunkerScopeID.EXPECTED:
                    expectation.set_expected_wtt(idx, (vessel_name, *key), factor)
                else:
                    expectation.set_existing_wtt(idx, (vessel_name, *key), factor)


def _assign_regulation_ttw_factors(regulation: Regulation,
                                   vessels: dict[str, Vessel],
                                   timeline: np.ndarray,
                                   idx: int) -> None:
    """
    Calculates and assigns the TTW emission factors related to a given regulation.

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

                    if ttw_supplied is not None:
                        ttw_consumption = ttw_supplied
                        ttw_slip = 0.  # TODO: change if deciding to split input
                    else:
                        ttw_consumption, ttw_slip = _calculate_converter_ttw(converter, fuel, emission, include_slip)

                    factor_consumption = _apply_gwp(ttw_consumption, regulation, emission)
                    factor_slip = _apply_gwp(ttw_slip, regulation, emission)

                    expectation.set_ttw_consumption(idx, (converter_name, *key), factor_consumption)
                    expectation.set_ttw_slip(idx, (converter_name, *key), factor_slip)


def _assign_regulation_emission_coefficients(regulation: Regulation,
                                             vessels: dict[str, Vessel],
                                             bunker_scope: BunkerScopeID,
                                             idx: int) -> None:
    """
    Calculates and assigns the emission coefficients related to a given regulation.

    Parameters
    ----------
    regulation
        Regulation to calculate emission coefficients for.
    vessels
        All vessels in the simulation.
    bunker_scope
        ID of the bunker scope.
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

                coefficient = 0.
                for emission in target_emissions:
                    coefficient += _calculate_regulation_emission_factor(regulation, vessel, converter, fuel,
                                                                         emission, bunker_scope, idx)

                key = (vessel_name, converter_name, fuel_name)

                if bunker_scope == BunkerScopeID.EXPECTED:
                    regulation.expectation.set_expected_coefficient(idx, key, coefficient)
                else:
                    regulation.expectation.set_existing_coefficient(idx, key, coefficient)


def _calculate_regulation_emission_factor(regulation: Regulation,
                                          vessel: Vessel,
                                          converter: Converter,
                                          fuel: Fuel,
                                          emission: Emission,
                                          bunker_scope: BunkerScopeID,
                                          idx: int) -> np.ndarray:
    """
    Calculate the emission factor in ton emissions/ton fuels for a given emission used in the calculation of a
    regulation emission coefficient.

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
    bunker_scope
        ID of the bunker scope.
    idx
        Current time-step index.

    Returns
    -------
    Emission factor.
    """

    vessel_name = vessel.name
    converter_name = converter.name
    fuel_name = fuel.name
    emission_name = emission.name

    key_wtt = (vessel_name, fuel_name, emission_name)
    key_ttw = (converter_name, fuel_name, emission_name)

    return _calculate_emission_factor(regulation, key_wtt, key_ttw, bunker_scope, idx)


def _assign_levy_emission_factors(levy: Levy,
                                  vessels: dict[str, Vessel],
                                  bunker_scope: BunkerScopeID,
                                  timeline: np.ndarray,
                                  idx: int) -> None:
    """
    Calculates and assigns the WTT and TTW emission factors related to a given levy.

    Parameters
    ----------
    levy
        Levy to calculate emission factor for.
    vessels
        All vessels in the simulation.
    bunker_scope
        ID of the bunker scope.
    timeline
        Simulation timeline.
    idx
        Current time-step index.
    """

    scope = levy.scope

    if scope in (PolicyScopeID.WTT, PolicyScopeID.WTW):
        _assign_levy_wtt_factors(levy, bunker_scope, timeline, idx)

    if scope in (PolicyScopeID.TTW, PolicyScopeID.WTW):
        _assign_levy_ttw_factors(levy, vessels, timeline, idx)

    _assign_levy_emission_coefficients(levy, vessels, bunker_scope, idx)


def _assign_levy_wtt_factors(levy: Levy,
                             bunker_scope: BunkerScopeID,
                             timeline: np.ndarray,
                             idx: int) -> None:
    """
    Calculates and assigns the WTT emission factor related to a given levy.

    Parameters
    ----------
    levy
        Levy to calculate emission factor for.
    bunker_scope
        ID of the bunker scope.
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

        for emission in target_emissions:
            emission_name = emission.name

            # user-supplied WTT (None falls back to the port-specific model
            # value resolved inside the per-port loop below).
            key = (fuel_name, emission_name)
            supplied = fuel_wtts[key]
            wtt_supplied = supplied.get(timeline[idx:]) if supplied is not None else None

            for port in levy.jurisdiction:
                port_name = port.name

                if not port.is_bunkering_allowed(fuel_name):
                    factor = np.nan
                else:
                    if wtt_supplied is not None:
                        wtt = wtt_supplied
                    else:
                        wtt = _get_port_bunker_wtt(port, fuel, emission, idx)

                    factor = _apply_gwp(wtt, levy, emission)

                if bunker_scope == BunkerScopeID.EXPECTED:
                    expectation.set_expected_wtt(idx, (port_name, *key), factor)
                else:
                    expectation.set_existing_wtt(idx, (port_name, *key), factor)


def _assign_levy_ttw_factors(levy: Levy,
                             vessels: dict[str, Vessel],
                             timeline: np.ndarray,
                             idx: int) -> None:
    """
    Calculates and assigns the TTW emission factors related to a given levy.

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

            for emission in target_emissions:
                emission_name = emission.name

                key = (vessel_name, fuel_name, emission_name)
                ttw = fuel_ttws[(fuel_name, emission_name)]

                if ttw is not None:
                    # user-supplied TTW applies uniformly with zero slip
                    ttw_consumption = ttw.get(timeline[idx:])
                    ttw_slip = 0.  # TODO: change if deciding to split input
                else:
                    # otherwise approximate as a power/efficiency weighted average
                    # across the converters in the vessel's power system
                    ttw_consumption, ttw_slip = _average_ttw_over_converters(vessel, fuel, emission, include_slip)

                factor_consumption = _apply_gwp(ttw_consumption, levy, emission)
                factor_slip = _apply_gwp(ttw_slip, levy, emission)

                expectation.set_ttw_consumption(idx, key, factor_consumption)
                expectation.set_ttw_slip(idx, key, factor_slip)


def _assign_levy_emission_coefficients(levy: Levy,
                                       vessels: dict[str, Vessel],
                                       bunker_scope: BunkerScopeID,
                                       idx: int) -> None:
    """
    Calculates and assigns the emission coefficients related to a given levy.

    Parameters
    ----------
    levy
        Levy to calculate emission coefficients for.
    vessels
        All vessels in the simulation.
    bunker_scope
        ID of the bunker scope.
    idx
        Current time-step index.
    """

    target_emissions = levy.emissions

    for vessel_name, vessel in vessels.items():

        usable_fuels = vessel.usable_fuels
        target_fuels = _usable_target_fuels(levy, usable_fuels)

        # find the ports that overlap between the
        # vessel route and the levy jurisdiction
        ports = list_intersection(vessel.route.ports, levy.jurisdiction)

        for port in ports:

            port_name = port.name

            for fuel in target_fuels:
                fuel_name = fuel.name

                if not port.is_bunkering_allowed(fuel_name):
                    continue

                coefficient = 0.
                for emission in target_emissions:
                    coefficient += _calculate_levy_emission_factor(levy, vessel, port, fuel, emission, bunker_scope, idx)

                coefficient = _calculate_threshold_adjusted_levy_emission_coefficient(coefficient, levy, fuel)

                key = (vessel_name, port_name, fuel_name)

                if bunker_scope == BunkerScopeID.EXPECTED:
                    levy.expectation.set_expected_coefficient(idx, key, coefficient)
                else:
                    levy.expectation.set_existing_coefficient(idx, key, coefficient)


def _calculate_levy_emission_factor(levy: Levy,
                                    vessel: Vessel,
                                    port: Port,
                                    fuel: Fuel,
                                    emission: Emission,
                                    bunker_scope: BunkerScopeID,
                                    idx: int) -> np.ndarray:
    """
    Calculate the emission factor in ton emissions/ton fuels for a given emission used in the calculation of a
    levy emission coefficient.

    This method takes input in the form of a single time-step index during the bunker algorithm
    but also a slice of indices for calculation of the adjusted fuel TCO.

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
    bunker_scope
        ID of the bunker scope.
    idx
        Time-step index.

    Returns
    -------
    Emission factor.
    """

    vessel_name = vessel.name
    port_name = port.name
    fuel_name = fuel.name
    emission_name = emission.name

    key_wtt = (port_name, fuel_name, emission_name)
    key_ttw = (vessel_name, fuel_name, emission_name)

    return _calculate_emission_factor(levy, key_wtt, key_ttw, bunker_scope, idx)


def _calculate_threshold_adjusted_levy_emission_coefficient(coefficient: float | np.ndarray,
                                                            levy: Levy,
                                                            fuel: Fuel) -> float | np.ndarray:
    """
    Calculate the threshold adjusted levy emission coefficient.

    Parameters
    ----------
    coefficient
        Emission coefficient in ton emission/ton fuel.
    levy
        Levy to calculate emission coefficient for.
    fuel
        Fuel for which the emissions coefficient is calculated.

    Returns
    -------
    The reference adjusted emission coefficient in ton emission/ton fuel.
    """

    scheme = levy.scheme

    lhv = fuel.lower_heating_value.get()
    lower_threshold = levy.lower_threshold.get()
    upper_threshold_obj = levy.upper_threshold
    upper_threshold = upper_threshold_obj.get() if upper_threshold_obj is not None else None

    coefficient_ref = (coefficient / lhv * TON_PER_GJ_TO_GRAM_PR_MJ) - lower_threshold

    if scheme == LevySchemeID.PENALTY:
        coefficient_ref = np.maximum(coefficient_ref, 0.)
    elif scheme == LevySchemeID.SUBSIDY:
        coefficient_ref = np.minimum(coefficient_ref, 0.)

    if scheme != LevySchemeID.SUBSIDY and upper_threshold is not None:
        coefficient_ref = np.minimum(coefficient_ref, upper_threshold - lower_threshold)

    return coefficient_ref * lhv / TON_PER_GJ_TO_GRAM_PR_MJ


def _calculate_converter_ttw(converter: Converter,
                             fuel: Fuel,
                             emission: Emission,
                             include_slip: bool) -> tuple[float, float]:
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
    Consumption TTW and slip TTW.
    """

    emission_name = emission.name
    fuel_type = fuel.fuel_type

    if fuel_type not in converter.get_fuel_types():
        return 0., 0.

    slip = converter.slip_fraction[fuel_type].get()

    # fuel-bound TTW emissions scale with burned fraction (1 - slip)
    ttw_consumption = (1. - slip) * fuel.ttw[emission_name].get()

    # consumption emissions per ton fuel-in, no slip scaling
    ttw_consumption += converter.consumption_ttw[(fuel_type, emission_name)].get()

    # slip emissions: X per ton fuel-in, gated by emission fuel_type
    ttw_slip = 0.
    if include_slip:
        emission_fuel_type = emission.fuel_type
        if emission_fuel_type == fuel_type:
            ttw_slip = slip

    return ttw_consumption, ttw_slip


def _average_wtt_over_ports(ports: list[Port],
                            fuel: Fuel,
                            emission: Emission,
                            idx: int) -> float | np.ndarray:
    """
    Estimate a converter's WTT emissions as a supply-weighted average over the
    ports on the vessel's route that intersect with the policy jurisdiction and
    allow bunkering of the fuel.

    The weighting is evaluated per time-step, as the supply of a fuel at a port
    may change over time (e.g. plants coming online). Ports without supply of
    the fuel carry no weight; otherwise they would dilute the average with a
    bunker WTT of 0 even though no fuel can be bunkered there. At time-steps
    where one or more ports have an infinite supply (e.g. unconstrained
    producers or liquid-market fuels) those ports dominate the market and are
    weighted equally, ignoring the finite-supply ports.

    Relies on the import calculation having transferred bunker supply and WTT
    to the port expectations; the two are written together there, so the
    weights and the averaged values always stem from the same snapshot.

    Parameters
    ----------
    ports
        List of ports in which the fuel can be bunkered in.
    fuel
        Fuel being spent.
    emission
        Emission.
    idx
        Current time-step index.

    Returns
    -------
    Approximate converter WTT.
    """

    fuel_name = fuel.name
    from_idx = np.s_[idx:]

    supplies = []
    wtts = []

    for port in ports:

        if not port.is_bunkering_allowed(fuel_name):
            continue

        supplies.append(port.expectation.get_bunker_supply(fuel_name, from_idx))
        wtts.append(_get_port_bunker_wtt(port, fuel, emission, idx))

    if not supplies:
        return 0.

    supply = np.stack(supplies)
    wtt = np.stack(wtts)

    # ports with a supply below tolerance carry no weight
    weights = np.where(supply > TOLERANCE, supply, 0.)

    # ports with an infinite supply dominate the market at that time-step
    # and are weighted equally, ignoring the finite-supply ports
    infinite = np.isinf(supply)
    weights = np.where(infinite.any(axis=0), infinite, weights)

    return divide_nonzero((weights * wtt).sum(axis=0), weights.sum(axis=0))


def _average_ttw_over_converters(vessel: Vessel,
                                 fuel: Fuel,
                                 emission: Emission,
                                 include_slip: bool) -> tuple[float, float]:
    """
    Estimate a port's TTW emissions as a power/efficiency weighted average over
    the converters in the vessel's power system that can burn the fuel.

    Parameters
    ----------
    vessel
        Vessel on which the fuel is spent.
    fuel
        Fuel being spent.
    emission
        Emission.
    include_slip
        Whether slip is included in the calculation of the levy TTW.

    Returns
    -------
    Approximate consumption TTW and slip TTW tied to a port.
    """

    fuel_type = fuel.fuel_type

    weighted_consumption_sum = 0.
    weighted_slip_sum = 0.
    weight_total = 0.

    for converter in vessel.power_system.get_converters():

        # skip converters that cannot burn this fuel so they
        # contribute no weight to the average; calling
        # _calculate_converter_ttw would return zeros but still
        # consume a weight and bias the result toward zero.
        if fuel_type not in converter.get_fuel_types():
            continue

        consumption, slip = _calculate_converter_ttw(converter, fuel, emission, include_slip)

        # power-efficiency weight for the weighted average
        power = converter.power_capacity.get()
        efficiency = converter.efficiency.get()
        weight = power / efficiency

        weighted_consumption_sum += weight * consumption
        weighted_slip_sum += weight * slip
        weight_total += weight

    ttw_consumption = divide_nonzero(weighted_consumption_sum, weight_total)
    ttw_slip = divide_nonzero(weighted_slip_sum, weight_total)

    return ttw_consumption, ttw_slip


def _calculate_emission_factor(policy: Levy | Regulation,
                               key_wtt: tuple[str, ...],
                               key_ttw: tuple[str, ...],
                               bunker_scope: BunkerScopeID,
                               idx: int) -> np.ndarray:
    """
    Generic method used for calculating the emission factor (from pre-defined WTT and TTW emission factors)
    for both levies and regulations.

    Parameters
    ----------
    policy
        The Levy or Regulation being calculated.
    key_wtt
        The key to the WTT attribute of the policy profile.
    key_ttw
        The key to the TTW attributes of the policy profile.
    bunker_scope
        ID of the bunker scope.
    idx
        Time-step index.

    Returns
    -------
    Emission factor.
    """

    from_idx = np.s_[idx:]

    expectation = policy.expectation

    if bunker_scope == BunkerScopeID.EXPECTED:
        wtt = expectation.get_expected_wtt(key_wtt, from_idx)
    else:
        wtt = expectation.get_existing_wtt(key_wtt, from_idx)

    ttw_consumption = expectation.get_ttw_consumption(key_ttw, from_idx)
    ttw_slip = expectation.get_ttw_slip(key_ttw, from_idx)

    # during calculation of the WTT and TTWs
    # results are adjusted for scope, inclusion
    # of slip, etc. so that reconstruction of the
    # emission factor can be made without checks
    factor = wtt + ttw_consumption + ttw_slip

    return factor


def _apply_gwp(emission_factor: float | np.ndarray,
               policy: Levy | Regulation,
               emission: Emission) -> float | np.ndarray:
    """
    Convert an emission factor to CO2-equivalent units by multiplying with the policy's GWP.

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
    GWP-weighted emission factor.
    """

    gwp = policy.expectation.get_global_warming_potential(emission.name)

    return emission_factor * gwp


def _usable_target_fuels(policy: Levy | Regulation, usable_fuels: dict[str, Fuel]) -> list[Fuel]:
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
    Targeted fuels also usable by the vessel.
    """

    return [fuel for fuel in policy.fuels if fuel.name in usable_fuels]


def _get_port_bunker_wtt(port: Port, fuel: Fuel, emission: Emission, idx: int) -> np.ndarray:
    """
    Extract the bunker WTT value at a port for a given fuel/emission, from `idx` onward.

    Parameters
    ----------
    port
        Port from which the WTT will be extracted.
    fuel
        Fuel for which the WTT will be extracted.
    emission
        Emission for which the WTT will be extracted.
    idx
        Current time-step index.

    Returns
    -------
    Bunker WTT emissions from `idx` onward.
    """

    from_idx = np.s_[idx:]

    fuel_name = fuel.name
    emission_name = emission.name
    wtt = port.expectation.get_bunker_wtt(fuel_name, emission_name, from_idx)

    return wtt
