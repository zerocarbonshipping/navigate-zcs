# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Residual energy demand of a vessel after a technology package, and its savings."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.util import divide_nonzero, energy_to_power, power_to_energy

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandID
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.core.types_ import CurveInput
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_residual_energy(
    vessel: Vessel,
    package: TechnologyPackage,
    idx: int | slice,
) -> tuple[dict[EnergyDemandID, FloatArray], dict[EnergyDemandID, FloatArray]]:
    """
    Calculate a vessel's residual energy demand at sea and in port with a package.

    The package's combined savings and external powers reduce the operational energy
    demand of each sailing condition and port, and its power transfers move energy
    between the energy demand types by the converter loads.

    Parameters
    ----------
    vessel
        Vessel providing the operational energy demand and the converters.
    package
        Technology package holding the precomputed savings, powers and transfer curves.
    idx
        Time-step index or slice of the evaluation.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Residual energy at sea per energy demand type, the condition axis first, in
        GJ/year.
    dict[EnergyDemandID, FloatArray]
        Residual energy in port per energy demand type, the port axis first, in
        GJ/year.
    """
    expectation = vessel.expectation

    raw_demand_sea = _stack_steps(expectation.get_operational_energy_sea_condition(idx))
    raw_demand_port = _stack_steps(expectation.get_operational_energy_port(idx))

    if package.is_empty:
        return raw_demand_sea, raw_demand_port

    times_sea = np.asarray(expectation.get_time_sea_condition(idx), dtype=float)
    times_port = np.asarray(expectation.get_time_port(idx), dtype=float)

    residual_sea = _calculate_residuals(vessel, package, times_sea, raw_demand_sea)
    residual_port = _calculate_residuals(vessel, package, times_port, raw_demand_port)

    return residual_sea, residual_port


def calculate_net_energy(
    raw_energies: Mapping[EnergyDemandID, FloatArray],
    savings: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, list[FloatLike]]:
    """
    Apply per-step saving fractions to the raw energy demand of each energy type.

    Parameters
    ----------
    raw_energies
        Raw energy demand per energy demand type and step, in GJ/year.
    savings
        Saving per energy demand type and step, fraction.

    Returns
    -------
    dict[EnergyDemandID, list[FloatLike]]
        Net energy demand per energy demand type and step, in GJ/year.
    """
    net_energies: dict[EnergyDemandID, list[FloatLike]] = {}

    for energy_id, raw_energy in raw_energies.items():
        steps = zip(raw_energy, savings[energy_id], strict=True)
        net_energies[energy_id] = [(1.0 - saving) * energy for energy, saving in steps]

    return net_energies


def scale_per_key(
    energies: Mapping[EnergyDemandID, Sequence[FloatLike] | FloatArray],
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


def calculate_energy_savings(
    net_energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
    raw_energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, list[float]]:
    """
    Calculate the saving fraction of each step's net energy against its raw energy.

    A step without raw energy saves nothing.

    Parameters
    ----------
    net_energies
        Net energy demand per energy demand type and step, in GJ/year.
    raw_energies
        Raw energy demand per energy demand type and step, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, list[float]]
        Saving per energy demand type and step, fraction.
    """
    savings: dict[EnergyDemandID, list[float]] = {}

    for energy_id, net_energy in net_energies.items():
        steps = zip(net_energy, raw_energies[energy_id], strict=True)
        remaining = [divide_nonzero(net, raw, default=1.0) for net, raw in steps]
        savings[energy_id] = [1.0 - float(ratio) for ratio in remaining]

    return savings


def _stack_steps(
    energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, FloatArray]:
    """Stack the energy of each step into one array per type, the step axis first."""
    return {key: np.asarray(value, dtype=float) for key, value in energies.items()}


def _calculate_residuals(
    vessel: Vessel,
    package: TechnologyPackage,
    times: FloatArray,
    raw_demands: Mapping[EnergyDemandID, FloatArray],
) -> dict[EnergyDemandID, FloatArray]:
    """
    Calculate the residual energy of each sailing condition or port.

    The combined saving and the external energy over each step's duration reduce the
    demand, floored at zero, before any power transfer moves energy between the
    types. Only the energy demand types of the given demands take part: there is no
    propulsion in port.

    Parameters
    ----------
    vessel
        Vessel whose converters set the loads.
    package
        Technology package installed on the vessel.
    times
        Time spent on each step, in days/year.
    raw_demands
        Operational energy demand per energy demand type, the step axis first, in
        GJ/year.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Residual energy per energy demand type, the step axis first, in GJ/year.
    """
    residuals: dict[EnergyDemandID, FloatArray] = {}

    for energy_id, raw_demand in raw_demands.items():
        saving = package.energy_saving[energy_id]
        power = package.external_power[energy_id]

        net_demand = raw_demand * (1.0 - saving)
        external_energy = power_to_energy(power, times)
        residuals[energy_id] = np.maximum(net_demand - external_energy, 0.0)

    if not package.transfers_power:
        return residuals

    return _subtract_transfers(vessel, package, times, residuals)


def _subtract_transfers(
    vessel: Vessel,
    package: TechnologyPackage,
    times: FloatArray,
    residuals: Mapping[EnergyDemandID, FloatArray],
) -> dict[EnergyDemandID, FloatArray]:
    """
    Reduce each sink's residual energy by the energy transferred into it.

    The source's residual power before any transfer sets its converter's load, and
    the energy every transfer into a sink moves over the step's duration is
    subtracted from the sink's residual, floored at zero.

    Parameters
    ----------
    vessel
        Vessel whose converters set the loads.
    package
        Technology package holding the transfer curves.
    times
        Time spent on each step, in days/year.
    residuals
        Residual energy before the transfers per energy demand type, the step axis
        first, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Residual energy after the transfers per energy demand type, the step axis
        first, in GJ/year.
    """
    transferred = {key: np.zeros_like(value) for key, value in residuals.items()}

    for (source_id, sink_id), curves in package.transfer_curves.items():
        if source_id not in residuals or sink_id not in residuals:
            continue

        residual_power = energy_to_power(residuals[source_id], times)
        load = _calculate_converter_load(vessel, source_id, residual_power)
        transfer_power = _calculate_power_transfer(curves, load)
        transferred[sink_id] += power_to_energy(transfer_power, times)

    remaining: dict[EnergyDemandID, FloatArray] = {}

    for energy_id, residual in residuals.items():
        remaining[energy_id] = np.maximum(residual - transferred[energy_id], 0.0)

    return remaining


def _calculate_converter_load(
    vessel: Vessel, energy_id: EnergyDemandID, residual_power: FloatArray
) -> FloatArray:
    """Return the load of the converter serving a demand, fraction of capacity."""
    converter = vessel.get_converter(energy_id)
    capacity = converter.power_capacity.get()
    return residual_power / capacity


def _calculate_power_transfer(curves: list[CurveInput], load: FloatArray) -> FloatArray:
    """
    Sum the power the transfer curves of one (source, sink) pair move at a load.

    Parameters
    ----------
    curves
        Non-zero transfer curves of the pair.
    load
        Load of the source converter at each step, fraction.

    Returns
    -------
    FloatArray
        Power transferred from source to sink at each step, in MW.
    """
    powers = np.array([curve.get(load) for curve in curves])
    return np.sum(powers, axis=0, dtype=float)
