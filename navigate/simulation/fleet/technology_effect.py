# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Each vessel's energy demand after its installed technology.

Fleets that cannot retrofit take the average saving of those that can.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID
from navigate.simulation.fleet.composition import get_multiplier
from navigate.simulation.fleet.operation import transfer_operational_savings
from navigate.simulation.fleet.residual_energy import (
    calculate_energy_savings,
    calculate_net_energy,
    calculate_residual_energy,
)
from navigate.simulation.fleet.trip import bind_conditions_to_legs, sum_energy_per_leg
from navigate.util import sum_per_key

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike


@dataclass
class _TechnologyEffect:
    """
    Uptake-weighted technology effect on a vessel type, over (increment, package).

    Parameters
    ----------
    saving_sea
        Weighted saving in each sailing condition, operational minus residual
        energy, GJ/year.
    saving_port
        Weighted saving at each port call, GJ/year.
    weight
        Total uptake weight, which normalizes the averages, number of vessels.
    shore_capacity
        Weighted shore power capacity, MW.
    """

    saving_sea: dict[EnergyDemandID, FloatArray]
    saving_port: dict[EnergyDemandID, FloatArray]
    weight: float = 0.0
    shore_capacity: float = 0.0


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

    for v, vessel in enumerate(fleet.vessels):
        op_sea, op_port = _apply_operational_savings(vessel, idx)
        op_sea_arr = {d: np.asarray(op_sea[d], dtype=float) for d in EnergyDemandID}
        op_port_arr = {
            d: np.asarray(op_port[d], dtype=float) for d in PORT_ENERGY_DEMANDS
        }

        effect = _accumulate_technology_effect(
            fleet, v, vessel, op_sea_arr, op_port_arr, idx
        )
        _transfer_residual_energy(vessel, op_sea_arr, op_port_arr, effect, idx)


def _apply_operational_savings(
    vessel: Vessel, idx: int
) -> tuple[
    dict[EnergyDemandID, list[FloatArray]], dict[EnergyDemandID, list[FloatArray]]
]:
    """
    Apply the operational saving fractions to the vessel's raw energy demand.

    The operational savings are zero-cost reductions such as JIT and weather routing.
    The result is stored on the expectation and the profile.

    Parameters
    ----------
    vessel
        Vessel to apply the operational savings for.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandID, list[FloatArray]]
        Operational energy at sea per energy demand type and condition, GJ/year.
    dict[EnergyDemandID, list[FloatArray]]
        Operational energy in port per energy demand type and port call, GJ/year.
    """
    expectation = vessel.expectation

    raw_sea = expectation.get_raw_energy_sea_condition(idx=idx)
    raw_port = expectation.get_raw_energy_port(idx=idx)

    saving_sea = expectation.get_operational_saving_fraction_sea()
    saving_port = expectation.get_operational_saving_fraction_port()

    op_sea = {
        d: [
            np.asarray(condition, dtype=float) * (1.0 - saving_sea[d])
            for condition in raw_sea[d]
        ]
        for d in EnergyDemandID
    }
    op_port = {
        d: [
            np.asarray(port, dtype=float) * (1.0 - saving_port[d])
            for port in raw_port[d]
        ]
        for d in PORT_ENERGY_DEMANDS
    }

    condition_legs = bind_conditions_to_legs(vessel.route)
    op_sea_leg = sum_energy_per_leg(condition_legs, op_sea)

    expectation.set_operational_energy_sea_condition(idx, op_sea)
    expectation.set_operational_energy_sea_leg(idx, op_sea_leg)
    expectation.set_operational_energy_port(idx, op_port)

    vessel.profile.set_operational_energy_sea(idx, sum_per_key(op_sea))
    vessel.profile.set_operational_energy_port(idx, sum_per_key(op_port))

    return op_sea, op_port


def _accumulate_technology_effect(
    fleet: Fleet,
    vessel_idx: int,
    vessel: Vessel,
    op_sea_arr: dict[EnergyDemandID, FloatArray],
    op_port_arr: dict[EnergyDemandID, FloatArray],
    idx: int,
) -> _TechnologyEffect:
    """
    Accumulate the uptake-weighted technology effect over (increment, package) pairs.

    A technology saving is the operational energy less the residual energy.

    Parameters
    ----------
    fleet
        Fleet owning the increments and technology packages.
    vessel_idx
        Index of `vessel` in `fleet.vessels`.
    vessel
        Vessel to accumulate the effect for.
    op_sea_arr
        Operational energy at sea per demand type, one array over conditions, GJ/year.
    op_port_arr
        Operational energy in port per demand type, one array over ports, GJ/year.
    idx
        Current time-step index.

    Returns
    -------
    _TechnologyEffect
        The accumulated effect.
    """
    route = vessel.route
    n_conditions = len(route.get_conditions())
    n_ports = route.get_number_of_ports()

    effect = _TechnologyEffect(
        {d: np.zeros(n_conditions, dtype=float) for d in EnergyDemandID},
        {d: np.zeros(n_ports, dtype=float) for d in PORT_ENERGY_DEMANDS},
    )

    for inc in fleet.increments[vessel_idx]:
        uptake = inc.package_uptake

        for p, package in enumerate(fleet.technology_packages):
            w = float(inc.multiplier) * float(uptake[p])
            if w <= 0.0:
                continue

            residual_sea, residual_port = calculate_residual_energy(
                vessel, package, np.s_[idx]
            )

            for demand, residual in residual_sea.items():
                effect.saving_sea[demand] += w * (op_sea_arr[demand] - residual)

            for demand, residual in residual_port.items():
                effect.saving_port[demand] += w * (op_port_arr[demand] - residual)

            effect.weight += w
            effect.shore_capacity += w * package.shore_power_capacity

    return effect


def _transfer_residual_energy(
    vessel: Vessel,
    op_sea_arr: dict[EnergyDemandID, FloatArray],
    op_port_arr: dict[EnergyDemandID, FloatArray],
    effect: _TechnologyEffect,
    idx: int,
) -> None:
    """
    Store the averaged technology effect's shore power and residual energy demand.

    Parameters
    ----------
    vessel
        Vessel to store the results for.
    op_sea_arr
        Operational energy at sea per demand type, one array over conditions, GJ/year.
    op_port_arr
        Operational energy in port per demand type, one array over ports, GJ/year.
    effect
        Accumulated technology effect.
    idx
        Current time-step index.
    """
    avg_shore_capacity = (
        effect.shore_capacity / effect.weight if effect.weight > 0.0 else 0.0
    )
    vessel.expectation.set_shore_power_capacity(idx, avg_shore_capacity)

    # without any uptake weight the residual energy stays the operational energy
    if effect.weight <= 0.0:
        avg_residual_sea = op_sea_arr
        avg_residual_port = op_port_arr
    else:
        inv_w = 1.0 / effect.weight
        avg_residual_sea = {
            d: op_sea_arr[d] - effect.saving_sea[d] * inv_w for d in EnergyDemandID
        }
        avg_residual_port = {
            d: op_port_arr[d] - effect.saving_port[d] * inv_w
            for d in PORT_ENERGY_DEMANDS
        }

    condition_legs = bind_conditions_to_legs(vessel.route)
    avg_residual_sea_leg = sum_energy_per_leg(condition_legs, avg_residual_sea)

    vessel.expectation.set_energy_sea_condition(idx, avg_residual_sea)
    vessel.expectation.set_energy_sea_leg(idx, avg_residual_sea_leg)
    vessel.expectation.set_energy_port(idx, avg_residual_port)

    vessel.profile.set_energy_sea(idx, sum_per_key(avg_residual_sea))
    vessel.profile.set_energy_port(idx, sum_per_key(avg_residual_port))


def approximate_missing_technology(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Estimate the energy-efficiency savings of the fleets that cannot retrofit.

    The average saving of the fleets that can retrofit applies to the energy demand
    of every fleet allowing the approximation. It carries no cost, so the cost of the
    efficiency improvements is underestimated.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    average_saving_sea, average_saving_port = _average_retrofit_savings(fleets, idx)

    for fleet in fleets.values():
        if fleet.can_retrofit() or not fleet.allow_technology_approximation:
            continue

        for vessel in fleet.vessels:
            _apply_approximated_saving(
                vessel, average_saving_sea, average_saving_port, idx
            )


def _average_retrofit_savings(
    fleets: dict[str, Fleet], idx: int
) -> tuple[dict[EnergyDemandID, float], dict[EnergyDemandID, float]]:
    """
    Calculate the energy-weighted average technology saving of retrofit-capable fleets.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.

    Returns
    -------
    dict[EnergyDemandID, float]
        Average saving at sea per demand type, fraction.
    dict[EnergyDemandID, float]
        Average saving in port per demand type, fraction.
    """
    average_saving_sea = dict.fromkeys(EnergyDemandID, 0.0)
    average_saving_port = dict.fromkeys(PORT_ENERGY_DEMANDS, 0.0)

    weight_sea = dict.fromkeys(average_saving_sea, 0.0)
    weight_port = dict.fromkeys(average_saving_port, 0.0)

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

            savings_sea = calculate_energy_savings(energy_sea, raw_energy_sea)
            savings_port = calculate_energy_savings(energy_port, raw_energy_port)

            _accumulate_energy_weighted_saving(
                raw_energy_sea, savings_sea, multiplier, average_saving_sea, weight_sea
            )
            _accumulate_energy_weighted_saving(
                raw_energy_port,
                savings_port,
                multiplier,
                average_saving_port,
                weight_port,
            )

    for k in average_saving_sea:
        average_saving_sea[k] = (
            (average_saving_sea[k] / weight_sea[k]) if weight_sea[k] else 0.0
        )
    for k in average_saving_port:
        average_saving_port[k] = (
            (average_saving_port[k] / weight_port[k]) if weight_port[k] else 0.0
        )

    return average_saving_sea, average_saving_port


def _accumulate_energy_weighted_saving(
    raw_energy: Mapping[EnergyDemandID, Sequence[FloatLike]],
    savings: Mapping[EnergyDemandID, Sequence[float]],
    multiplier: float,
    saving_totals: dict[EnergyDemandID, float],
    weight_totals: dict[EnergyDemandID, float],
) -> None:
    """
    Accumulate one vessel's energy-weighted saving fractions into the running totals.

    Parameters
    ----------
    raw_energy
        Raw energy demand per demand type, one value per condition or port call,
        GJ/year; with `multiplier`, it weights the accumulation.
    savings
        Saving per demand type, one value per condition or port call, fraction.
    multiplier
        Number of vessels of this type.
    saving_totals
        Running weighted saving sums per demand type; updated in place.
    weight_totals
        Running weight sums per demand type; updated in place.
    """
    for k in saving_totals:
        for step, raw in enumerate(raw_energy[k]):
            weight = float(raw) * multiplier
            saving_totals[k] += savings[k][step] * weight
            weight_totals[k] += weight


def _apply_approximated_saving(
    vessel: Vessel,
    average_saving_sea: dict[EnergyDemandID, float],
    average_saving_port: dict[EnergyDemandID, float],
    idx: int,
) -> None:
    """
    Apply the fleet-average savings to one vessel's operational energy and store it.

    Parameters
    ----------
    vessel
        Vessel to apply the approximated savings to.
    average_saving_sea
        Average saving at sea per demand type, fraction.
    average_saving_port
        Average saving in port per demand type, fraction.
    idx
        Current time-step index.
    """
    op_sea = vessel.expectation.get_operational_energy_sea_condition(idx=idx)
    op_port = vessel.expectation.get_operational_energy_port(idx=idx)

    sav_sea = {
        k: [average_saving_sea[k]] * len(op_sea[k])
        for k in average_saving_sea
        if k in op_sea
    }

    sav_port = {
        k: [average_saving_port[k]] * len(op_port[k])
        for k in average_saving_port
        if k in op_port
    }

    net_sea = calculate_net_energy(op_sea, sav_sea)
    net_port = calculate_net_energy(op_port, sav_port)

    condition_legs = bind_conditions_to_legs(vessel.route)
    net_sea_leg = sum_energy_per_leg(condition_legs, net_sea)

    vessel.expectation.set_energy_sea_condition(idx, net_sea)
    vessel.expectation.set_energy_sea_leg(idx, net_sea_leg)
    vessel.expectation.set_energy_port(idx, net_port)

    vessel.profile.set_energy_sea(
        idx, {k: float(np.sum(np.asarray(net_sea[k]))) for k in net_sea}
    )
    vessel.profile.set_energy_port(
        idx, {k: float(np.sum(np.asarray(net_port[k]))) for k in net_port}
    )
