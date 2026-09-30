# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Residual energy demand of a vessel after the effects of a technology package."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.unit import MWD_TO_GJ

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandTypeID
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import CurveInput
    from navigate.fleet.package import Package
    from navigate.util.types_ import FloatLike


def calculate_residual_energy(
    vessel: Vessel,
    package: Package,
    idx: int | slice,
) -> tuple[
    dict[EnergyDemandTypeID, list[FloatLike]],
    dict[EnergyDemandTypeID, list[FloatLike]],
]:
    """
    Calculate a vessel's residual energy demand at sea and in port with a package.

    The package's combined savings and external powers reduce the operational energy
    demand of each leg and port, and its power transfers move energy between the
    energy demand types by the converter loads.

    Parameters
    ----------
    vessel
        Vessel providing the operational energy demand and the power system.
    package
        Package holding the precomputed savings, powers and transfer curves.
    idx
        Time-step index or slice of the evaluation.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatLike]]
        Residual energy at sea per energy demand type and leg, GJ/year.
    dict[EnergyDemandTypeID, list[FloatLike]]
        Residual energy in port per energy demand type and port, GJ/year.
    """
    times_sea = vessel.expectation.get_time_sea(idx)
    times_port = vessel.expectation.get_time_port(idx)
    raw_demand_sea = vessel.expectation.get_operational_energy_sea(idx=idx)
    raw_demand_port = vessel.expectation.get_operational_energy_port(idx=idx)

    if package.is_empty:
        return raw_demand_sea, raw_demand_port

    energy_sea = _iterate_legs_or_ports(vessel, package, times_sea, raw_demand_sea)
    energy_port = _iterate_legs_or_ports(vessel, package, times_port, raw_demand_port)

    return energy_sea, energy_port


def net_energy_from_raw(
    raw_energies: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    savings: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
) -> dict[EnergyDemandTypeID, list[FloatLike]]:
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
    dict[EnergyDemandTypeID, list[FloatLike]]
        Net energy demand per energy demand type and step, GJ/year.
    """
    out: dict[EnergyDemandTypeID, list[FloatLike]] = {}
    for k, raw in raw_energies.items():
        sav = savings[k]
        out[k] = [(1.0 - s) * e for e, s in zip(raw, sav, strict=True)]
    return out


def _iterate_legs_or_ports(
    vessel: Vessel,
    package: Package,
    durations: Sequence[FloatLike],
    raw_demands: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
) -> dict[EnergyDemandTypeID, list[FloatLike]]:
    """
    Calculate the residual energy of each leg or port.

    Per step, the combined saving and the external energy over the step's duration
    reduce the demand; with power transfers, the residual power sets each
    converter's load, and the power the transfers move over the duration reduces the
    sink's residual, floored at zero. Only the energy demand types of the given
    demands take part: there is no propulsion in port.

    Parameters
    ----------
    vessel
        Vessel whose converters set the loads.
    package
        Package installed on the vessel.
    durations
        Time spent on each step, days/year.
    raw_demands
        Operational energy demand per energy demand type and step, GJ/year.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatLike]]
        Residual energy per energy demand type and step, GJ/year.
    """
    keys = list(raw_demands.keys())
    n_steps = len(durations)
    residual_energy_all: dict[EnergyDemandTypeID, list[FloatLike]] = {
        energy_id: [] for energy_id in keys
    }

    for i in range(n_steps):
        residual_energy: dict[EnergyDemandTypeID, FloatLike] = {}
        loads: dict[EnergyDemandTypeID, FloatLike] = {}
        duration = durations[i]

        for energy_id in keys:
            raw_demand = raw_demands[energy_id][i]
            compound_saving = package.compound_savings[energy_id]
            compound_power = package.compound_powers[energy_id]

            energy_external = _power_to_energy(compound_power, duration)
            residual_energy[energy_id] = _raw_to_residual_energy(
                raw_demand, compound_saving, energy_external
            )

            if not package.includes_transfer:
                continue

            residual_power = _energy_to_power(residual_energy[energy_id], duration)
            loads[energy_id] = _calculate_converter_load(
                vessel, energy_id, residual_power
            )

        if package.includes_transfer:
            for sink_energy_id in keys:
                if sink_energy_id not in residual_energy:
                    continue

                transfer_energy: FloatLike = 0.0

                for power_system_id in keys:
                    if power_system_id not in loads:
                        continue

                    pair = (power_system_id, sink_energy_id)
                    if pair not in package.transfer_curves:
                        continue

                    load = loads[power_system_id]
                    transfer_power = _calculate_power_transfer(
                        package.transfer_curves[pair], load
                    )
                    transfer_energy += _power_to_energy(transfer_power, duration)

                residual_energy[sink_energy_id] = np.maximum(
                    residual_energy[sink_energy_id] - transfer_energy, 0.0
                )

        for energy_id in keys:
            residual_energy_all[energy_id].append(residual_energy[energy_id])

    return residual_energy_all


def _calculate_power_transfer(curves: list[CurveInput], load: FloatLike) -> FloatLike:
    """
    Sum the power the transfer curves of one (source, sink) pair move at a load.

    Parameters
    ----------
    curves
        Non-zero transfer curves of the pair.
    load
        Load of the source converter, fraction.

    Returns
    -------
    FloatLike
        Power transferred from source to sink, MW.
    """
    powers = np.array([curve.get(load) for curve in curves])
    transfer: FloatLike = np.sum(powers, axis=0, dtype=float)
    return transfer


def _calculate_converter_load(
    vessel: Vessel, power_system_id: EnergyDemandTypeID, residual_power: FloatLike
) -> FloatLike:
    """Return the load of the converter serving a demand, fraction of capacity."""
    converter = vessel.power_system.get_converter_by_energy_type(power_system_id)
    capacity = converter.power_capacity.get()
    return residual_power / capacity


def _raw_to_residual_energy(
    raw_energy: FloatLike, saving: float, external_power: FloatLike
) -> FloatLike:
    """Reduce the raw energy by the saving and the external energy, floored at zero."""
    residual: FloatLike = np.maximum(raw_energy * (1.0 - saving) - external_power, 0.0)
    return residual


def _power_to_energy(power: FloatLike, duration: FloatLike) -> FloatLike:
    """Convert a power, MW, over a duration, days, to energy, GJ."""
    return power * duration * MWD_TO_GJ


def _energy_to_power(energy: FloatLike, duration: FloatLike) -> FloatLike:
    """Convert an energy, GJ, over a duration, days, to power, MW."""
    return energy / (duration * MWD_TO_GJ)
