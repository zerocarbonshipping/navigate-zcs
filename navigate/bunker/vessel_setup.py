# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.fuel import Emission, Fuel
    from navigate.vessel import Converter, Vessel

import navigate.core.enum_ as enum_
from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID
from navigate.core.unit import TON_TO_KG


def get_effective_lhv(converter: Converter, fuel: Fuel) -> float:
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


def calculate_emission_factor_TTW(
    vessel: Vessel, converter: Converter, fuel: Fuel, emission: Emission, idx: int,
) -> float:
    """
    Calculate the TTW emission factor for an emission from consuming a fuel in a specific converter and vessel.
    Should be multiplied by the amount of spent fuel in that converter.

    The emission factor accounts for slip:
    - Fuel-bound (TTW) emissions scale with burned fraction (1 - slip).
    - Consumption emissions are per ton fuel-in and not scaled.
    - Slip emissions are per ton fuel-in, gated by emission fuel_type.

    Parameters
    ----------
    vessel
        Vessel on which the fuel is consumed.
    converter
        Converter the fuel is consumed in.
    fuel
        Fuel being consumed.
    emission
        Emission node.
    idx
        Current time-step index.

    Returns
    -------
    float
        TTW emission factor (ton emission / ton fuel-in).
    """

    emission_name = emission.get_name()
    fuel_type = fuel.fuel_type

    if fuel_type not in converter.get_fuel_types():
        return 0.

    slip = converter.get_slip_fraction(fuel_type).get()

    # fuel-bound TTW emissions scale with burned fraction
    EF = (1. - slip) * fuel.get_TTW(emission_name).get()

    # consumption emissions per ton fuel-in, no slip scaling
    EF += converter.get_consumption_TTW(fuel_type, emission_name).get()

    # slip emissions: slip per ton fuel-in, gated by emission fuel_type
    emission_fuel_type = emission.fuel_type
    if emission_fuel_type == fuel_type:
        EF += slip

    return EF


def build_vessel_specifics(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Build technical vessel details used across various member methods such as adding variables, constraints,
    and transferring results.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel being initiated.
    """

    v = vessel.get_name()

    alg.converters[v] = {c.get_name(): c for c in vessel.power_system.get_converters()}

    # converters that serve port energy demands (ELECTRICAL, HEAT — not PROPULSION)
    power_system = vessel.power_system
    alg.port_converters[v] = {power_system.get_converter_by_energy_type(energy_type).get_name():
                              power_system.get_converter_by_energy_type(energy_type)
                              for energy_type in enum_.EnergyDemandTypePortID}

    # the reference only has to be created once
    # although usable fuels changes over time
    alg.usable_fuels[v] = vessel.usable_fuels
    alg.converter_fuels[v] = {c: {f: fuel for f, fuel in alg.usable_fuels[v].items()
                                  if fuel.fuel_type in converter.get_fuel_types()}
                              for c, converter in alg.converters[v].items()}

    route = vessel.route

    n_ports = route.get_number_of_ports()
    n_legs = route.get_number_of_legs()
    port_idx = tuple(i for i in range(n_ports))

    if route.route_type == enum_.RouteTypeID.ROUND_TRIP:
        leg_idx = tuple((i, (i + 1) % n_legs) for i in range(n_legs))
    else:
        # all possible port-to-port combinations
        # required for regulatory purposes
        leg_idx = tuple((i, j) for i in range(n_ports) for j in range(n_ports))

    alg.port_idx[v] = port_idx
    alg.leg_idx[v] = leg_idx

    # pre-compute converter efficiencies and effective LHV values
    eff_v = {}
    for c, converter in alg.converters[v].items():
        eff_v[c] = converter.efficiency.get()
        for f, fuel in alg.converter_fuels[v][c].items():
            lhv = get_effective_lhv(converter, fuel)
            alg.effective_lhv[(v, c, f)] = lhv
    alg.efficiency[v] = eff_v

    # pre-compute port name to index mapping
    ports = route.ports
    pn2i = {}
    for pi, port in enumerate(ports):
        pn2i.setdefault(port.get_name(), []).append(pi)
    alg.port_name_to_indices[v] = pn2i


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

    v = vessel.get_name()

    for c, converter in alg.converters[v].items():
        for f, fuel in alg.converter_fuels[v][c].items():
            for e, emission in alg.emissions.items():
                TTW = calculate_emission_factor_TTW(vessel, converter, fuel, emission, alg.idx)
                alg.emission_factor[(v, c, f, e)] = TTW


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

    v = vessel.get_name()

    active_regulations = alg.active_regulations
    effective_lhv = alg.effective_lhv
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
               for c in alg.converters[v]
               for f in alg.converter_fuels[v][c]
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

            sp_ef = 0.
            for emission in regulation.emissions:
                emission_name = emission.get_name()
                ef = port_expectation.get_shore_power_emission_factor(emission_name, idx)
                ef = ef * regulation.expectation.get_global_warming_potential(emission_name)

                sp_ef += ef

            # shore power is already in GJ, so effective_lhv equivalent is 1.0
            sp_coeff = sp_ef - (
                thresholds[(r, v)] / TON_TO_KG * 1.0
                if regulation.measure == RegulationMeasureID.INTENSITY
                else 0.)

            alg.shore_power_regulation_ef[(v, p, r)] = sp_ef
            alg.shore_power_regulation_coeff[(v, p, r)] = sp_coeff


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

    v = vessel.get_name()
    ports = vessel.route.ports
    port_levies = alg.port_levies
    is_expected = alg.scope == BunkerScopeID.EXPECTED
    idx = alg.idx
    usable_fuels = alg.usable_fuels[v]

    alg.cost_levy.update({(v, port.get_name(), f, levy.get_name()):

                          levy.expectation.get_level(idx)

                          * (levy.expectation.get_expected_coefficient((v, port.get_name(), f), idx)
                             if is_expected else
                             levy.expectation.get_existing_coefficient((v, port.get_name(), f), idx))

                          for port in ports
                          for levy in port_levies[port.get_name()]
                          for f in usable_fuels

                          if port.is_bunkering_allowed(f)
                          if levy.is_active() and levy.vessel_is_policed(v)})
