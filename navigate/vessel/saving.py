# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.calculator.curve import Curve
from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.unit import MWD_TO_GJ
from navigate.vessel import Vessel
from navigate.vessel.package import Package


def calculate_residual_energy(vessel: Vessel,
                              package: Package,
                              idx: int | slice,
                              ) -> tuple[dict[EnergyDemandTypeID, list[float | np.ndarray]],
                                         dict[EnergyDemandTypeID, list[float | np.ndarray]]]:
    """
    Calculate the residual energy demand for a vessel during its operations at sea and in port.

    This function computes the vessel's time-resolved residual energy demand by combining:
    (i) raw operational energy demand, (ii) compound savings from efficiency technologies,
    and (iii) external/alternative power contributions. It evaluates the operational profile
    separately for sea and port phases, applies technology uptakes, and accounts for power
    transfers across energy systems.

    Internally, the function:
      1. Retrieves time axes and raw demands for sea and port phases.
      2. Uses the precomputed compound technology effects from the Package:
         - energy savings (multiplicative efficiency across technologies)
         - installed/available external power (additive, weighted by uptakes)
      3. Iterates over each step (leg/port call) to produce residuals by energy type,
         including cross-system transfers based on converter loads and technology-defined
         power transfer characteristics.

    The result is two lists (sea, port), each containing a dictionary per step with residual
    energy time series for the energy demand types present in that phase.


    Parameters
    ----------
    vessel
        The vessel object providing operational expectations and power system properties.
    package
        Package containing precomputed savings, powers, and transfer curves.
    idx
        Time index or slice selecting the operational window.

    Returns
    -------
    tuple
        A tuple of two lists:
          - Residual energy at sea: list of dictionaries keyed by energy demand type.
          - Residual energy in port: list of dictionaries keyed by energy demand type.
    """

    times_sea = vessel.expectation.get_time_sea(idx)
    times_port = vessel.expectation.get_time_port(idx)
    raw_demand_sea = vessel.expectation.get_operational_energy_sea(idx=idx)
    raw_demand_port = vessel.expectation.get_operational_energy_port(idx=idx)

    if package.is_empty:
        return raw_demand_sea, raw_demand_port

    energy_sea = _iterate_legs_or_ports(vessel,
                                        package,
                                        times_sea,
                                        raw_demand_sea)

    energy_port = _iterate_legs_or_ports(vessel,
                                         package,
                                         times_port,
                                         raw_demand_port)

    return energy_sea, energy_port


def _iterate_legs_or_ports(vessel: Vessel,
                           package: Package,
                           durations: list[np.ndarray],
                           raw_demands: dict[EnergyDemandTypeID, list[np.ndarray]],
                           ) -> dict[EnergyDemandTypeID, list[float | np.ndarray]]:
    """
    Iterate over legs or ports and compute residual energy for each step.

    For each time step, the algorithm:
      1. Converts compound external power to energy over the step duration and subtracts it
         from the raw demand after applying compound savings.
      2. Converts the resulting residual energy back to power to determine per-system loads
         via the vessel's converters.
      3. Applies cross-system power transfers between all available source/sink energy types,
         integrates those transfers over the duration, and subtracts from the residuals
         (non-negatively).

    Only energy types present in the input raw demands for the given context (e.g., PROPULSION
    is not present in port) contribute to step-level residuals and loads; transfers are applied
    against the computed residuals accordingly.


    Parameters
    ----------
    vessel
        The vessel being analyzed.
    package
        Package of technologies installed on the vessel.
    durations
        Time arrays per step; used to convert between power and energy.
    raw_demands
        Raw energy demand per energy type and step for the selected context.

    Returns
    -------
        One entry per step: a dictionary mapping energy demand type to residual energy.
    """

    keys = list(raw_demands.keys())
    n_steps = len(durations)
    residual_energy_all = {energy_id: [] for energy_id in keys}

    for i in range(n_steps):

        residual_energy = {}
        loads = {}
        duration = durations[i]

        for energy_id in keys:

            raw_demand = raw_demands[energy_id][i]
            compound_saving = package.compound_savings[energy_id]
            compound_power = package.compound_powers[energy_id]

            energy_external = _power_to_energy(compound_power, duration)
            residual_energy[energy_id] = _raw_to_residual_energy(raw_demand, compound_saving, energy_external)

            if not package.includes_transfer:
                continue

            residual_power = _energy_to_power(residual_energy[energy_id], duration)
            loads[energy_id] = _calculate_converter_load(vessel, energy_id, residual_power)

        if package.includes_transfer:

            for sink_energy_id in keys:

                if sink_energy_id not in residual_energy:
                    continue

                transfer_energy = 0.

                for power_system_id in keys:

                    if power_system_id not in loads:
                        continue

                    pair = (power_system_id, sink_energy_id)
                    if pair not in package.transfer_curves:
                        continue

                    load = loads[power_system_id]
                    transfer_power = _calculate_power_transfer(package.transfer_curves[pair], load)
                    transfer_energy += _power_to_energy(transfer_power, duration)

                residual_energy[sink_energy_id] = np.maximum(residual_energy[sink_energy_id] - transfer_energy, 0.)

        for energy_id in keys:
            residual_energy_all[energy_id].append(residual_energy[energy_id])

    return residual_energy_all


def _calculate_power_transfer(curves: list[Curve | Scalar],
                              load: np.ndarray) -> np.ndarray:
    """
    Compute power transfer from pre-filtered non-zero curves.

    Only called for (src, dst) pairs known to have at least one non-zero
    contributing technology.  No dict lookups or tuple hashing required.

    Parameters
    ----------
    curves
        Non-zero Curve/Scalar objects for this (source, sink) pair.
    load
        Source system load used as input to each transfer response.

    Returns
    -------
    np.ndarray
        Power transferred from source to sink for the given load.
    """

    powers = np.array([curve.get(load) for curve in curves])
    return np.sum(powers, axis=0, dtype=float)


def _calculate_converter_load(vessel: Vessel,
                              power_system_id: EnergyDemandTypeID,
                              residual_power: np.ndarray) -> np.ndarray:
    """
    Convert residual power to per-converter load.

    Retrieves the converter capacity for the given energy system and normalizes the
    residual power by that capacity to obtain the converter load.
    """

    converter = vessel.power_system.get_converter_by_energy_type(power_system_id)
    capacity = converter.power_capacity.get()
    return residual_power / capacity


def _raw_to_residual_energy(raw_energy: np.ndarray, saving: float, external_power: np.ndarray) -> np.ndarray:
    """
    Convert raw energy to residual energy after savings and external power.

    Applies the compound saving to the raw demand, subtracts external energy, and clamps
    the result to non-negative values.
    """
    return np.maximum(raw_energy * (1. - saving) - external_power, 0.)


def _power_to_energy(power: float | np.ndarray, duration: np.ndarray) -> np.ndarray:
    """
    Power-to-energy conversion over the provided duration.

    Multiplies power by duration and unit conversion to obtain energy.
    """
    return power * duration * MWD_TO_GJ


def _energy_to_power(energy: np.ndarray, duration: np.ndarray) -> np.ndarray:
    """
    Energy-to-power conversion over the provided duration.

    Divides energy by duration and unit conversion to obtain power.
    """
    return energy / (duration * MWD_TO_GJ)
