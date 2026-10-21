# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Each vessel's energy demand after its installed technology.

Fleets that cannot retrofit take the ratio of residual to raw energy of those that can.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID
from navigate.simulation.fleet.composition import get_multiplier
from navigate.simulation.fleet.operation import transfer_operational_savings
from navigate.simulation.fleet.residual_energy import calculate_residual_energy
from navigate.simulation.fleet.trip import bind_conditions_to_legs, sum_energy_per_leg
from navigate.util import divide_nonzero, sum_per_key

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.util.types_ import FloatArray, FloatLike


def update_residual_energy_demand(fleet: Fleet, idx: int) -> None:
    """
    Update every vessel's residual energy demand after technology installation.

    Parameters
    ----------
    fleet
        Fleet whose vessels are updated.
    idx
        Current time-step index.
    """
    transfer_operational_savings(fleet)
    packages = fleet.technology_packages

    for vessel, increments in zip(fleet.vessels, fleet.increments, strict=True):
        sea, port = _calculate_operational_energy(vessel, idx)
        _transfer_operational_energy(vessel, sea, port, idx)

        # a vessel type without technology uptake keeps its operational energy
        weights = _calculate_package_weights(increments, packages)
        shore = 0.0
        if weights:
            sea, port, shore = _calculate_technology_effect(vessel, weights, idx)

        _transfer_residual_energy(vessel, sea, port, idx)
        vessel.expectation.set_shore_power_capacity(idx, shore)


def _calculate_operational_energy(
    vessel: Vessel, idx: int
) -> tuple[dict[EnergyDemandID, FloatArray], dict[EnergyDemandID, FloatArray]]:
    """
    Calculate the vessel's raw energy demand less its operational savings.

    The operational savings are zero-cost reductions such as JIT and weather routing.

    Parameters
    ----------
    vessel
        Vessel to calculate the operational energy for.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Operational energy at sea per energy demand type, one value per condition, in
        GJ/year.
    dict[EnergyDemandID, FloatArray]
        Operational energy in port per energy demand type, one value per port call, in
        GJ/year.
    """
    expectation = vessel.expectation

    raw_sea = expectation.get_raw_energy_sea_condition(idx=idx)
    raw_port = expectation.get_raw_energy_port(idx=idx)

    saving_sea = expectation.get_operational_saving_fraction_sea()
    saving_port = expectation.get_operational_saving_fraction_port()

    remaining_sea = {key: 1.0 - value for key, value in saving_sea.items()}
    remaining_port = {key: 1.0 - value for key, value in saving_port.items()}

    sea = _scale_per_key(raw_sea, remaining_sea)
    port = _scale_per_key(raw_port, remaining_port)

    return sea, port


def _transfer_operational_energy(
    vessel: Vessel,
    sea: Mapping[EnergyDemandID, FloatArray],
    port: Mapping[EnergyDemandID, FloatArray],
    idx: int,
) -> None:
    """
    Store the vessel's operational energy demand on its expectation and results.

    Parameters
    ----------
    vessel
        Vessel to store the operational energy for.
    sea
        Operational energy at sea per energy demand type, one value per condition, in
        GJ/year.
    port
        Operational energy in port per energy demand type, one value per port call, in
        GJ/year.
    idx
        Current time-step index.
    """
    expectation = vessel.expectation
    results = vessel.results

    condition_legs = bind_conditions_to_legs(vessel.route)
    sea_leg = sum_energy_per_leg(condition_legs, sea)

    expectation.set_operational_energy_sea_condition(idx, sea)
    expectation.set_operational_energy_sea_leg(idx, sea_leg)
    expectation.set_operational_energy_port(idx, port)

    totals_sea = sum_per_key(sea)
    totals_port = sum_per_key(port)

    for key, values in results.operational_energy_sea.items():
        values[idx] = totals_sea[key]

    for key, values in results.operational_energy_port.items():
        values[idx] = totals_port[key]


def _calculate_package_weights(
    increments: Sequence[VesselIncrement], packages: Sequence[TechnologyPackage]
) -> dict[TechnologyPackage, float]:
    """
    Calculate the number of vessels of a type carrying each technology package.

    Parameters
    ----------
    increments
        Age cohorts of the vessel type.
    packages
        Technology packages of the fleet.

    Returns
    -------
    dict[TechnologyPackage, float]
        Vessels carrying each package, summed over the cohorts, for the packages
        carried at all, number of vessels.
    """
    weights = dict.fromkeys(packages, 0.0)

    for increment in increments:
        uptake = zip(packages, increment.package_uptake, strict=True)

        for package, share in uptake:
            weights[package] += increment.multiplier * float(share)

    return {package: weight for package, weight in weights.items() if weight > 0.0}


def _calculate_technology_effect(
    vessel: Vessel, weights: Mapping[TechnologyPackage, float], idx: int
) -> tuple[dict[EnergyDemandID, FloatArray], dict[EnergyDemandID, FloatArray], float]:
    """
    Average the residual energy and shore power capacity over the vessel's packages.

    Parameters
    ----------
    vessel
        Vessel providing the operational energy demand.
    weights
        Vessels carrying each package, summed over the cohorts, for the packages
        carried at all, number of vessels.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Residual energy at sea per energy demand type, one value per condition, in
        GJ/year.
    dict[EnergyDemandID, FloatArray]
        Residual energy in port per energy demand type, one value per port call, in
        GJ/year.
    float
        Shore power capacity, in MW.
    """
    residuals_sea = []
    residuals_port = []

    for package in weights:
        residual_sea, residual_port = calculate_residual_energy(vessel, package, idx)
        residuals_sea.append(residual_sea)
        residuals_port.append(residual_port)

    package_weights = list(weights.values())
    capacities = [package.shore_power_capacity for package in weights]

    sea = _average_per_key(residuals_sea, package_weights)
    port = _average_per_key(residuals_port, package_weights)
    shore = float(np.average(capacities, weights=package_weights))

    return sea, port, shore


def _average_per_key(
    energies: Sequence[Mapping[EnergyDemandID, FloatArray]], weights: Sequence[float]
) -> dict[EnergyDemandID, FloatArray]:
    """
    Average the energy of each demand type over the packages, weighted by uptake.

    Parameters
    ----------
    energies
        Energy per energy demand type of each package, in GJ/year.
    weights
        Vessels carrying each package, summed over the cohorts, number of vessels.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Weighted average energy per energy demand type, in GJ/year.
    """
    averages: dict[EnergyDemandID, FloatArray] = {}

    for energy_id in energies[0]:
        stacked = [energy[energy_id] for energy in energies]
        averages[energy_id] = np.average(stacked, axis=0, weights=weights)

    return averages


def _transfer_residual_energy(
    vessel: Vessel,
    sea: Mapping[EnergyDemandID, FloatArray],
    port: Mapping[EnergyDemandID, FloatArray],
    idx: int,
) -> None:
    """
    Store the vessel's residual energy demand on its expectation and results.

    Parameters
    ----------
    vessel
        Vessel to store the residual energy for.
    sea
        Residual energy at sea per energy demand type, one value per condition, in
        GJ/year.
    port
        Residual energy in port per energy demand type, one value per port call, in
        GJ/year.
    idx
        Current time-step index.
    """
    expectation = vessel.expectation
    results = vessel.results

    condition_legs = bind_conditions_to_legs(vessel.route)
    sea_leg = sum_energy_per_leg(condition_legs, sea)

    expectation.set_energy_sea_condition(idx, sea)
    expectation.set_energy_sea_leg(idx, sea_leg)
    expectation.set_energy_port(idx, port)

    totals_sea = sum_per_key(sea)
    totals_port = sum_per_key(port)

    for key, values in results.energy_sea.items():
        values[idx] = totals_sea[key]

    for key, values in results.energy_port.items():
        values[idx] = totals_port[key]


def approximate_missing_technology(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Estimate the energy-efficiency savings of the fleets that cannot retrofit.

    The fleet-wide ratio of residual to raw energy of the fleets that can retrofit
    scales the operational energy of every fleet allowing the approximation. It
    carries no cost, so the cost of the efficiency improvements is underestimated.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    ratio_sea, ratio_port = _calculate_retrofit_ratios(fleets, idx)

    for fleet in fleets.values():
        if fleet.can_retrofit() or not fleet.allow_technology_approximation:
            continue

        for vessel in fleet.vessels:
            sea, port = _calculate_approximation(vessel, ratio_sea, ratio_port, idx)
            _transfer_residual_energy(vessel, sea, port, idx)


def _calculate_retrofit_ratios(
    fleets: dict[str, Fleet], idx: int
) -> tuple[dict[EnergyDemandID, float], dict[EnergyDemandID, float]]:
    """
    Calculate the ratio of residual to raw energy over the retrofit-capable fleets.

    Each ratio sums every condition or port call of every vessel, weighted by its
    number of vessels. A demand type without raw energy keeps its energy.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandID, float]
        Ratio at sea per energy demand type, fraction.
    dict[EnergyDemandID, float]
        Ratio in port per energy demand type, fraction.
    """
    residual_sea = dict.fromkeys(EnergyDemandID, 0.0)
    residual_port = dict.fromkeys(PORT_ENERGY_DEMANDS, 0.0)
    raw_sea = dict.fromkeys(EnergyDemandID, 0.0)
    raw_port = dict.fromkeys(PORT_ENERGY_DEMANDS, 0.0)

    for fleet in fleets.values():
        if not fleet.can_retrofit():
            continue

        for v, vessel in enumerate(fleet.vessels):
            multiplier = get_multiplier(fleet, v)
            expectation = vessel.expectation

            energy_sea = expectation.get_energy_sea_condition(idx)
            energy_port = expectation.get_energy_port(idx)
            raw_energy_sea = expectation.get_raw_energy_sea_condition(idx)
            raw_energy_port = expectation.get_raw_energy_port(idx)

            _accumulate_weighted(residual_sea, energy_sea, multiplier)
            _accumulate_weighted(residual_port, energy_port, multiplier)
            _accumulate_weighted(raw_sea, raw_energy_sea, multiplier)
            _accumulate_weighted(raw_port, raw_energy_port, multiplier)

    ratio_sea = _divide_per_key(residual_sea, raw_sea)
    ratio_port = _divide_per_key(residual_port, raw_port)

    return ratio_sea, ratio_port


def _accumulate_weighted(
    totals: dict[EnergyDemandID, float],
    energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
    multiplier: float,
) -> None:
    """
    Add one vessel type's energy, times its number of vessels, to the running totals.

    Parameters
    ----------
    totals
        Running total per energy demand type, in GJ/year; updated in place.
    energies
        Energy per energy demand type, one value per condition or port call, in
        GJ/year.
    multiplier
        Number of vessels of the type.
    """
    for energy_id in totals:
        energy = np.asarray(energies[energy_id], dtype=float)
        totals[energy_id] += multiplier * float(np.sum(energy))


def _divide_per_key(
    residuals: Mapping[EnergyDemandID, float], raws: Mapping[EnergyDemandID, float]
) -> dict[EnergyDemandID, float]:
    """
    Divide each demand type's residual energy by its raw energy, 1 without raw energy.

    Parameters
    ----------
    residuals
        Residual energy per energy demand type, in GJ/year.
    raws
        Raw energy per energy demand type, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, float]
        Ratio per energy demand type, fraction.
    """
    ratios: dict[EnergyDemandID, float] = {}

    for energy_id, residual in residuals.items():
        raw = raws[energy_id]
        ratios[energy_id] = float(divide_nonzero(residual, raw, default=1.0))

    return ratios


def _calculate_approximation(
    vessel: Vessel,
    ratio_sea: Mapping[EnergyDemandID, float],
    ratio_port: Mapping[EnergyDemandID, float],
    idx: int,
) -> tuple[dict[EnergyDemandID, FloatArray], dict[EnergyDemandID, FloatArray]]:
    """
    Scale the vessel's operational energy demand by the retrofit ratios.

    Parameters
    ----------
    vessel
        Vessel to approximate the residual energy for.
    ratio_sea
        Ratio of residual to raw energy at sea per energy demand type, fraction.
    ratio_port
        Ratio of residual to raw energy in port per energy demand type, fraction.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Approximated residual energy at sea per energy demand type, one value per
        condition, in GJ/year.
    dict[EnergyDemandID, FloatArray]
        Approximated residual energy in port per energy demand type, one value per
        port call, in GJ/year.
    """
    expectation = vessel.expectation

    operational_sea = expectation.get_operational_energy_sea_condition(idx=idx)
    operational_port = expectation.get_operational_energy_port(idx=idx)

    sea = _scale_per_key(operational_sea, ratio_sea)
    port = _scale_per_key(operational_port, ratio_port)

    return sea, port


def _scale_per_key(
    energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
    factors: Mapping[EnergyDemandID, float],
) -> dict[EnergyDemandID, FloatArray]:
    """
    Scale the energy of each demand type by its factor.

    Parameters
    ----------
    energies
        Energy per energy demand type, one value per condition or port call, in
        GJ/year.
    factors
        Factor per energy demand type, fraction.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Scaled energy per energy demand type, one value per condition or port call,
        in GJ/year.
    """
    scaled: dict[EnergyDemandID, FloatArray] = {}

    for energy_id, energy in energies.items():
        scaled[energy_id] = np.asarray(energy, dtype=float) * factors[energy_id]

    return scaled
