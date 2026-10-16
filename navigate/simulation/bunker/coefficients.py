# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Compute the per-time-step policy coefficients of the LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import RegulationMeasureID
from navigate.simulation.bunker.utils import get_converters
from navigate.util import TON_TO_KG

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


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
    expectation = vessel.expectation

    active_regulations = alg.active_regulations
    fuels_per_converter = alg.fuels_per_converter
    idx = alg.idx

    # evaluate the vessel thresholds once per build; non-policed vessels carry
    # a threshold of zero (their emission terms never enter a constraint), and
    # check_consistency guarantees every policed vessel a threshold
    thresholds: dict[tuple[str, str], float] = {}
    for r, regulation in active_regulations.items():
        threshold = regulation.vessel_threshold[v]
        if regulation.vessel_is_policed(v) and threshold is not None:
            thresholds[(r, v)] = threshold.get(alg.time)
        else:
            thresholds[(r, v)] = 0.0
    alg.regulation_vessel_threshold.update(thresholds)

    factors = {
        (v, c, f, r): regulation.expectation.get_coefficient((v, c, f), idx)
        for c in get_converters(vessel)
        for f in fuels_per_converter[v, c]
        for r, regulation in active_regulations.items()
    }

    coefficients = {
        (v, c, f, r): factor
        - (
            thresholds[(r, v)] / TON_TO_KG * expectation.get_effective_lhv(c, f)
            if active_regulations[r].measure == RegulationMeasureID.INTENSITY
            else 0.0
        )
        for (v, c, f, r), factor in factors.items()
    }

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
            shore_power_emission_factor = 0.0
            for emission in regulation.emissions:
                emission_name = emission.name
                emission_factor = float(
                    port_expectation.get_shore_power_emission_factor(emission_name, idx)
                )
                emission_factor *= regulation.expectation.get_global_warming_potential(
                    emission_name
                )

                shore_power_emission_factor += emission_factor

            # shore power is already in GJ, so its effective LHV is 1.0
            shore_power_coefficient = shore_power_emission_factor - (
                thresholds[(r, v)] / TON_TO_KG * 1.0
                if regulation.measure == RegulationMeasureID.INTENSITY
                else 0.0
            )

            alg.shore_power_regulation_emission_factor[(v, p, r)] = (
                shore_power_emission_factor
            )
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
    idx = alg.idx
    usable_fuels = vessel.usable_fuels

    alg.cost_levy.update(
        {
            (v, port.name, f, levy.name): levy.expectation.get_level(idx)
            * levy.expectation.get_coefficient((v, port.name, f), idx)
            for port in ports
            for levy in port.imposed_levies
            for f in usable_fuels
            if port.is_bunkering_allowed(f)
            if levy.vessel_is_policed(v)
        }
    )
