# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.utils import get_converters
from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID
from navigate.core.unit import TON_TO_KG


def _get_effective_lhv(converter: Converter, fuel: Fuel) -> float:
    """
    Effective LHV accounting for slip: (1 - slip) * LHV_raw.

    Parameters
    ----------
    converter
        Converter the fuel is consumed in.
    fuel
        Fuel being consumed.

    Returns
    -------
    float
        Effective lower heating value (GJ/ton fuel-in).
    """

    slip = converter.get_slip_fraction(fuel.fuel_type).get()
    return (1. - slip) * fuel.lower_heating_value.get()


def _calculate_emission_factor_TTW(converter: Converter, fuel: Fuel, emission: Emission) -> float:
    """
    Calculate the TTW emission factor for an emission from consuming a fuel in a specific converter.
    Should be multiplied by the amount of spent fuel in that converter.

    The emission factor accounts for slip:
    - Fuel-bound (TTW) emissions scale with burned fraction (1 - slip).
    - Consumption emissions are per ton fuel-in and not scaled.
    - Slip emissions are per ton fuel-in, gated by emission fuel_type.

    Parameters
    ----------
    converter
        Converter the fuel is consumed in.
    fuel
        Fuel being consumed.
    emission
        Emission node.

    Returns
    -------
    float
        TTW emission factor (ton emission / ton fuel-in).
    """

    emission_name = emission.name
    fuel_type = fuel.fuel_type

    if fuel_type not in converter.get_fuel_types():
        return 0.

    slip = converter.get_slip_fraction(fuel_type).get()

    # fuel-bound TTW emissions scale with burned fraction
    emission_factor = (1. - slip) * fuel.get_TTW(emission_name).get()

    # consumption emissions per ton fuel-in, no slip scaling
    emission_factor += converter.get_consumption_TTW(fuel_type, emission_name).get()

    # slip emissions: slip per ton fuel-in, gated by emission fuel_type
    emission_fuel_type = emission.fuel_type
    if emission_fuel_type == fuel_type:
        emission_factor += slip

    return emission_factor


def calculate_effective_lhv(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Pre-compute the effective LHV of every converter-fuel combination of a vessel.
    The values are read repeatedly when building constraints and transferring results.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which effective LHV values are computed.
    """

    v = vessel.name

    for c, converter in get_converters(vessel).items():
        for f, fuel in alg.fuels_per_converter[(v, c)].items():
            alg.effective_lhv[(v, c, f)] = _get_effective_lhv(converter, fuel)


def calculate_emission_factors(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Updates the emission factors for a given vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        The vessel object for which emission factors are to be updated.
    """

    v = vessel.name

    for c, converter in get_converters(vessel).items():
        for f, fuel in alg.fuels_per_converter[(v, c)].items():
            for e, emission in alg.emissions.items():
                alg.emission_factor[(v, c, f, e)] = _calculate_emission_factor_TTW(converter, fuel, emission)


def calculate_policy_coefficients(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Calculate the dynamic policy coefficients relevant for the current time-step.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which coefficients are calculated.
    """

    calculate_regulation_coefficients(alg, vessel)
    calculate_levy_coefficients(alg, vessel)


def calculate_regulation_coefficients(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Calculate the dynamic regulation coefficients relevant for the current time-step.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which coefficients are calculated.
    """

    v = vessel.name

    active_regulations = alg.active_regulations
    effective_lhv = alg.effective_lhv
    fuels_per_converter = alg.fuels_per_converter
    is_expected = alg.scope == BunkerScopeID.EXPECTED
    idx = alg.idx

    # evaluate the vessel thresholds once per build; non-policed vessels carry
    # a threshold of zero (their emission terms never enter a constraint)
    thresholds = {(r, v): (regulation.get_vessel_threshold(v).get(alg.time)
                           if regulation.vessel_is_policed(v) else 0.)
                  for r, regulation in active_regulations.items()}
    alg.regulation_vessel_threshold.update(thresholds)

    factors = {(v, c, f, r): (regulation.expectation.get_expected_coefficient((v, c, f), idx)
                              if is_expected else
                              regulation.expectation.get_existing_coefficient((v, c, f), idx))
               for c in get_converters(vessel)
               for f in fuels_per_converter[v, c]
               for r, regulation in active_regulations.items()}

    coefficients = {(v, c, f, r):
                    factor
                    - (thresholds[(r, v)] / TON_TO_KG * effective_lhv[(v, c, f)]
                       if active_regulations[r].measure == RegulationMeasureID.INTENSITY
                       else 0.)
                    for (v, c, f, r), factor in factors.items()}

    alg.regulation_emission_factor.update(factors)
    alg.regulation_spend_coefficient.update(coefficients)

    # shore power regulation coefficients
    route = vessel.route
    ports = route.ports

    for p, port in enumerate(ports):

        if (v, p) not in alg.shore_power:
            continue

        port_expectation = port.expectation

        for r, regulation in active_regulations.items():

            shore_power_emission_factor = 0.
            for emission in regulation.emissions:
                emission_name = emission.name
                emission_factor = port_expectation.get_shore_power_emission_factor(emission_name, idx)
                emission_factor *= regulation.expectation.get_global_warming_potential(emission_name)

                shore_power_emission_factor += emission_factor

            # shore power is already in GJ, so effective_lhv equivalent is 1.0
            shore_power_coefficient = shore_power_emission_factor - (
                thresholds[(r, v)] / TON_TO_KG * 1.0
                if regulation.measure == RegulationMeasureID.INTENSITY
                else 0.)

            alg.shore_power_regulation_emission_factor[(v, p, r)] = shore_power_emission_factor
            alg.shore_power_regulation_coefficient[(v, p, r)] = shore_power_coefficient


def calculate_levy_coefficients(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Calculate the dynamic levy coefficients relevant for the current time-step.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which coefficients are calculated.
    """

    v = vessel.name
    ports = vessel.route.ports
    port_levies = alg.port_levies
    is_expected = alg.scope == BunkerScopeID.EXPECTED
    idx = alg.idx
    usable_fuels = vessel.usable_fuels

    alg.cost_levy.update({(v, port.name, f, levy.name):

                          levy.expectation.get_level(idx)

                          * (levy.expectation.get_expected_coefficient((v, port.name, f), idx)
                             if is_expected else
                             levy.expectation.get_existing_coefficient((v, port.name, f), idx))

                          for port in ports
                          for levy in port_levies[port.name]
                          for f in usable_fuels

                          if port.is_bunkering_allowed(f)
                          if levy.is_active() and levy.vessel_is_policed(v)})
