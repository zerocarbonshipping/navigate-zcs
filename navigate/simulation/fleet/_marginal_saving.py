# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Marginal cost saving of a technology package or a speed change."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fleet._residual_energy import calculate_residual_energy
from navigate.simulation.fleet._trip import sum_energy_per_leg
from navigate.util import slice_dict_list

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandID
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.simulation.fleet._trip import ConditionLegs
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_marginal_technology_saving(
    vessel: Vessel,
    condition_legs: ConditionLegs,
    package: TechnologyPackage,
    idx: slice,
) -> FloatArray:
    """
    Calculate the marginal cost saving of installing a technology package.

    The change from the baseline energy to the residual energy after the package is
    valued at the technology-horizon shadow-price beliefs, summed at sea and in port.
    The baseline is the operational energy before any technology, so that installing
    nothing is an NPV=0 business case and a package saving less than the current
    average uptake still saves. For a package with a low saving potential the
    evaluation may then fall outside the optimal polytope, and the shadow price may
    underestimate the impact.

    Parameters
    ----------
    vessel
        Vessel on which the package is evaluated.
    condition_legs
        Leg of each sailing condition of the vessel's route.
    package
        Technology package holding the precomputed savings, powers and transfer curves.
    idx
        Time-steps of the evaluation.

    Returns
    -------
    FloatArray
        Marginal cost saving at each of the time-steps, in USD/year.
    """
    expectation = vessel.expectation

    residual_sea, residual_port = calculate_residual_energy(vessel, package, idx)
    residual_sea_leg = sum_energy_per_leg(condition_legs, residual_sea)

    baseline_sea = expectation.get_operational_energy_sea_leg(idx)
    baseline_port = expectation.get_operational_energy_port(idx)

    price_sea = slice_dict_list(expectation.get_belief_pi_sea_technology(), idx)
    price_port = slice_dict_list(expectation.get_belief_pi_port_technology(), idx)

    saving_sea = _sum_savings(residual_sea_leg, baseline_sea, price_sea)
    saving_port = _sum_savings(residual_port, baseline_port, price_port)

    # a slice of time-steps always yields an array
    return np.asarray(saving_sea + saving_port)


def calculate_marginal_speed_saving(
    vessel: Vessel,
    condition_legs: ConditionLegs,
    residual_sea: Mapping[EnergyDemandID, Sequence[FloatLike]],
    residual_port: Mapping[EnergyDemandID, Sequence[FloatLike]],
    idx: int,
) -> float:
    """
    Calculate the marginal cost saving of a speed change.

    The change from the energy of the last bunker solve, the optimal polytope's
    reference, to the residual energy at the new speed is valued at the speed-horizon
    shadow-price beliefs, summed at sea and in port. The residual energies must
    include the effect of the current technology uptake to match the reference.

    Parameters
    ----------
    vessel
        Vessel whose speed changes.
    condition_legs
        Leg of each sailing condition of the vessel's route.
    residual_sea
        Residual energy at sea per energy demand type and condition, in GJ/year.
    residual_port
        Residual energy in port per energy demand type and port, in GJ/year.
    idx
        Current time-step index.

    Returns
    -------
    float
        Marginal cost saving, in USD/year.
    """
    expectation = vessel.expectation

    residual_sea_leg = sum_energy_per_leg(condition_legs, residual_sea)

    baseline_sea = slice_dict_list(expectation.get_energy_conservation_rhs_sea(), idx)
    baseline_port = slice_dict_list(expectation.get_energy_conservation_rhs_port(), idx)

    price_sea = slice_dict_list(expectation.get_belief_pi_sea_speed(), idx)
    price_port = slice_dict_list(expectation.get_belief_pi_port_speed(), idx)

    saving_sea = _sum_savings(residual_sea_leg, baseline_sea, price_sea)
    saving_port = _sum_savings(residual_port, baseline_port, price_port)

    return float(saving_sea + saving_port)


def _sum_savings(
    residual_energy: Mapping[EnergyDemandID, FloatArray | Sequence[FloatLike]],
    baseline_energy: Mapping[EnergyDemandID, Sequence[FloatLike]],
    shadow_prices: Mapping[EnergyDemandID, Sequence[FloatLike]],
) -> FloatLike:
    """
    Sum the cost saved by moving each step's energy from the baseline to the residual.

    A step is a leg at sea or a port. The saving of a step is negative where its
    residual exceeds its baseline, as at a higher speed.

    Parameters
    ----------
    residual_energy
        Residual energy per energy demand type and step, in GJ/year.
    baseline_energy
        Baseline energy per energy demand type and step, in GJ/year.
    shadow_prices
        Shadow price per energy demand type and step, in USD/GJ.

    Returns
    -------
    FloatLike
        Cost saved, in USD/year.
    """
    saving: FloatLike = 0.0

    for energy_id, residuals in residual_energy.items():
        baselines = baseline_energy[energy_id]
        prices = shadow_prices[energy_id]
        for residual, baseline, price in zip(residuals, baselines, prices, strict=True):
            saving += price * (baseline - residual)

    return saving
