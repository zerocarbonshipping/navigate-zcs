# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Residual energy demand of a vessel after the effects of a technology package."""

from __future__ import annotations

from itertools import product
from typing import TYPE_CHECKING

import numpy as np

from navigate.util import MWD_TO_GJ, divide_nonzero

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
        Vessel providing the operational energy demand and the power system.
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

    times_sea = expectation.get_time_sea_condition(idx)
    times_port = expectation.get_time_port(idx)
    raw_demand_sea = expectation.get_operational_energy_sea_condition(idx=idx)
    raw_demand_port = expectation.get_operational_energy_port(idx=idx)

    if package.is_empty:
        return _stack_steps(raw_demand_sea), _stack_steps(raw_demand_port)

    energy_sea = _residual_energy(vessel, package, times_sea, raw_demand_sea)
    energy_port = _residual_energy(vessel, package, times_port, raw_demand_port)

    return energy_sea, energy_port


def net_energy_from_raw(
    raw_energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
    savings: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, list[FloatLike]]:
    """
    Apply per-step saving fractions to the raw energy demand of each energy type.

    Parameters
    ----------
    raw_energies
        Raw energy demand per energy demand type and step, GJ/year.
    savings
        Saving per energy demand type and step, fraction.

    Returns
    -------
    dict[EnergyDemandID, list[FloatLike]]
        Net energy demand per energy demand type and step, GJ/year.
    """
    out: dict[EnergyDemandID, list[FloatLike]] = {}
    for k, raw in raw_energies.items():
        sav = savings[k]
        out[k] = [(1.0 - s) * e for e, s in zip(raw, sav, strict=True)]
    return out


def _residual_energy(
    vessel: Vessel,
    package: TechnologyPackage,
    durations: Sequence[FloatLike],
    raw_demands: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, FloatArray]:
    """
    Calculate the residual energy of every sailing condition or port at once.

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
    durations
        Time spent on each step, in days/year.
    raw_demands
        Operational energy demand per energy demand type and step, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Residual energy per energy demand type, the step axis first, in GJ/year.
    """
    times = np.asarray(durations, dtype=float)
    residual_energy: dict[EnergyDemandID, FloatArray] = {}

    for energy_id, raw_demand in _stack_steps(raw_demands).items():
        saving = package.compound_savings[energy_id]
        external_energy = _power_to_energy(package.compound_powers[energy_id], times)
        residual_energy[energy_id] = _raw_to_residual_energy(
            raw_demand, saving, external_energy
        )

    if not package.includes_transfer:
        return residual_energy

    return _residual_energy_after_transfer(vessel, package, times, residual_energy)


def _residual_energy_after_transfer(
    vessel: Vessel,
    package: TechnologyPackage,
    times: FloatArray,
    residual_energy: Mapping[EnergyDemandID, FloatArray],
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
    residual_energy
        Residual energy before the transfers per energy demand type, the step axis
        first, in GJ/year.

    Returns
    -------
    dict[EnergyDemandID, FloatArray]
        Residual energy after the transfers per energy demand type, the step axis
        first, in GJ/year.
    """
    transfer_energy = {
        energy_id: np.zeros_like(energy)
        for energy_id, energy in residual_energy.items()
    }

    for source_id, sink_id in product(residual_energy, repeat=2):
        curves = package.transfer_curves.get((source_id, sink_id))
        if curves is None:
            continue

        residual_power = _energy_to_power(residual_energy[source_id], times)
        load = _calculate_converter_load(vessel, source_id, residual_power)
        transfer_power = _calculate_power_transfer(curves, load)
        transfer_energy[sink_id] += _power_to_energy(transfer_power, times)

    return {
        energy_id: np.maximum(energy - transfer_energy[energy_id], 0.0)
        for energy_id, energy in residual_energy.items()
    }


def _stack_steps(
    energies: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> dict[EnergyDemandID, FloatArray]:
    """Stack the energy of each step into one array per type, the step axis first."""
    return {
        energy_id: np.asarray(energy, dtype=float)
        for energy_id, energy in energies.items()
    }


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
    transfer: FloatArray = np.sum(powers, axis=0, dtype=float)
    return transfer


def _calculate_converter_load(
    vessel: Vessel, power_system_id: EnergyDemandID, residual_power: FloatArray
) -> FloatArray:
    """Return the load of the converter serving a demand, fraction of capacity."""
    converter = vessel.power_system.get_converter_by_energy_type(power_system_id)
    capacity = converter.power_capacity.get()
    return residual_power / capacity


def _raw_to_residual_energy(
    raw_energy: FloatArray, saving: float, external_energy: FloatArray
) -> FloatArray:
    """Reduce the raw energy by the saving and the external energy, floored at zero."""
    return np.maximum(raw_energy * (1.0 - saving) - external_energy, 0.0)


def _power_to_energy(power: FloatLike, duration: FloatArray) -> FloatArray:
    """Convert a power, MW, over a duration, days, to energy, GJ."""
    return power * duration * MWD_TO_GJ


def _energy_to_power(energy: FloatArray, duration: FloatArray) -> FloatArray:
    """Convert an energy, GJ, over a duration, days, to power, MW, zero without time."""
    return divide_nonzero(energy, duration * MWD_TO_GJ)
