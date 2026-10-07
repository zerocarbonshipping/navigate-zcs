# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Marginal cost saving of a technology package or a speed change."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.fleet.operation import convert_to_regional_steps
from navigate.simulation.fleet.residual_energy import calculate_residual_energy

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.enum_ import EnergyDemandTypeID
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.util.types_ import FloatArray, FloatLike


def get_smoothed_energy_duals_technology(
    vessel: Vessel,
) -> tuple[
    dict[EnergyDemandTypeID, list[FloatArray]],
    dict[EnergyDemandTypeID, list[FloatArray]],
]:
    """
    Return the per-leg shadow-price beliefs amortised over the technology horizon.

    Each (energy-demand-type, leg) belief is an EMA of the raw LP duals, so it keeps
    the LP's per-leg structure with the year-to-year volatility damped.

    Parameters
    ----------
    vessel
        Vessel whose beliefs are read.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatArray]]
        Smoothed shadow prices at sea per energy demand type and leg, USD/GJ.
    dict[EnergyDemandTypeID, list[FloatArray]]
        Smoothed shadow prices in port per energy demand type and port, USD/GJ.
    """
    expectation = vessel.expectation
    return (
        expectation.get_belief_pi_sea_technology(),
        expectation.get_belief_pi_port_technology(),
    )


def get_smoothed_energy_duals_speed(
    vessel: Vessel,
) -> tuple[
    dict[EnergyDemandTypeID, list[FloatArray]],
    dict[EnergyDemandTypeID, list[FloatArray]],
]:
    """
    Return the per-leg shadow-price beliefs amortised over the speed horizon.

    The speed horizon is shorter than the technology horizon, matched to the
    timescale of operational speed-management decisions.

    Parameters
    ----------
    vessel
        Vessel whose beliefs are read.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatArray]]
        Smoothed shadow prices at sea per energy demand type and leg, USD/GJ.
    dict[EnergyDemandTypeID, list[FloatArray]]
        Smoothed shadow prices in port per energy demand type and port, USD/GJ.
    """
    expectation = vessel.expectation
    return expectation.get_belief_pi_sea_speed(), expectation.get_belief_pi_port_speed()


def calculate_marginal_technology_saving(
    vessel: Vessel, package: TechnologyPackage, idx: slice
) -> FloatArray:
    """
    Calculate the marginal cost saving of installing a technology package.

    The change from the baseline energy to the residual energy after the package is
    valued at the smoothed shadow prices, summed at sea and in port. The baseline is
    the operational energy before any technology, so that installing nothing is an
    NPV=0 business case and a package saving less than the current average uptake
    still saves. For a package with a low saving potential the evaluation may then
    fall outside the optimal polytope, and the shadow price may underestimate the
    impact.

    Parameters
    ----------
    vessel
        Vessel on which the package is evaluated.
    package
        Technology package holding the precomputed savings, powers and transfer curves.
    idx
        Time-steps of the evaluation.

    Returns
    -------
    FloatArray
        Marginal cost saving at each of the time-steps, USD/year.
    """
    # the shadow prices are given per regional step, so the per-leg residual energy
    # is converted to regional steps
    residual_energy_sea, residual_energy_port = calculate_residual_energy(
        vessel, package, idx
    )
    residual_energy_sea = convert_to_regional_steps(vessel, residual_energy_sea)

    baseline_energy_sea = _as_step_arrays(
        vessel.expectation.get_regional_operational_energy_sea()
    )
    baseline_energy_port = _as_step_arrays(
        vessel.expectation.get_operational_energy_port()
    )

    shadow_price_sea, shadow_price_port = get_smoothed_energy_duals_technology(vessel)

    # a slice of time-steps always yields an array
    return np.asarray(
        _calculate_marginal_saving(
            residual_energy_sea,
            residual_energy_port,
            baseline_energy_sea,
            baseline_energy_port,
            shadow_price_sea,
            shadow_price_port,
            idx,
        )
    )


def calculate_marginal_speed_saving(
    vessel: Vessel,
    residual_energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    residual_energy_port: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    idx: int,
    smoothed_duals: tuple[
        Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
        Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    ],
) -> float:
    """
    Calculate the marginal cost saving of a speed change.

    The change from the energy of the last bunker solve, the optimal polytope's
    reference, to the residual energy at the new speed is valued at the smoothed
    shadow prices, summed at sea and in port. The residual energies must include the
    effect of the current technology uptake to match that reference.

    Parameters
    ----------
    vessel
        Vessel whose speed changes.
    residual_energy_sea
        Residual energy at sea per energy demand type and leg, GJ/year.
    residual_energy_port
        Residual energy in port per energy demand type and port, GJ/year.
    idx
        Current time-step index.
    smoothed_duals
        Shadow prices at sea and in port from ``get_smoothed_energy_duals_speed``,
        passed in because the speed optimisation calls this for every objective
        evaluation and the beliefs do not change between them.

    Returns
    -------
    float
        Marginal cost saving, USD/year.
    """
    residual_energy_sea = convert_to_regional_steps(vessel, residual_energy_sea)

    baseline_energy_sea = vessel.expectation.get_energy_conservation_rhs_sea()
    baseline_energy_port = vessel.expectation.get_energy_conservation_rhs_port()

    shadow_price_sea, shadow_price_port = smoothed_duals

    return float(
        _calculate_marginal_saving(
            residual_energy_sea,
            residual_energy_port,
            baseline_energy_sea,
            baseline_energy_port,
            shadow_price_sea,
            shadow_price_port,
            idx,
        )
    )


def _calculate_marginal_saving(
    residual_energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    residual_energy_port: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    baseline_energy_sea: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    baseline_energy_port: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    shadow_price_sea: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    shadow_price_port: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    idx: int | slice,
) -> FloatLike:
    """
    Sum the marginal savings at sea and in port.

    Parameters
    ----------
    residual_energy_sea
        Residual energy at sea per energy demand type and leg, GJ/year.
    residual_energy_port
        Residual energy in port per energy demand type and port, GJ/year.
    baseline_energy_sea
        Baseline energy at sea per energy demand type and leg, GJ/year.
    baseline_energy_port
        Baseline energy in port per energy demand type and port, GJ/year.
    shadow_price_sea
        Smoothed shadow prices at sea, USD/GJ.
    shadow_price_port
        Smoothed shadow prices in port, USD/GJ.
    idx
        Time-step index or slice.

    Returns
    -------
    FloatLike
        Marginal cost saving at sea and in port, USD/year.
    """
    savings_sea = _iterate_steps(
        residual_energy_sea, baseline_energy_sea, shadow_price_sea, idx
    )
    savings_port = _iterate_steps(
        residual_energy_port, baseline_energy_port, shadow_price_port, idx
    )

    return savings_sea + savings_port


def _iterate_steps(
    energies_residual: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
    energies_baseline: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    shadow_prices: Mapping[EnergyDemandTypeID, Sequence[FloatArray]],
    idx: int | slice,
) -> FloatLike:
    """
    Sum the dual-variable savings over all energy demand types and steps.

    Parameters
    ----------
    energies_residual
        Residual energy per energy demand type and step, GJ/year.
    energies_baseline
        Baseline energy per energy demand type and step, GJ/year.
    shadow_prices
        Shadow prices per energy demand type and step, USD/GJ.
    idx
        Time-step index or slice.

    Returns
    -------
    FloatLike
        Summed saving, USD/year.
    """
    savings: FloatLike = 0.0

    for energy_id, energy_residual in energies_residual.items():
        for step, energy_residual_step in enumerate(energy_residual):
            energy_baseline_step = energies_baseline[energy_id][step][idx]
            shadow_price = shadow_prices[energy_id][step][idx]

            savings += _calculate_dual_variable_saving(
                energy_residual_step, energy_baseline_step, shadow_price
            )

    return savings


def _calculate_dual_variable_saving(
    energy_residual: FloatLike,
    energy_baseline: FloatLike,
    shadow_price: FloatLike,
) -> FloatLike:
    """
    Calculate the cost saved by changing the energy from the baseline to the residual.

    The saving is negative when the residual exceeds the baseline, as at a higher
    speed.

    Parameters
    ----------
    energy_residual
        Energy after the speed change or the technology installation, GJ/year.
    energy_baseline
        Reference energy of the optimal polytope, GJ/year.
    shadow_price
        Shadow price of the energy requirement, USD/GJ.

    Returns
    -------
    FloatLike
        Cost saved, USD/year.
    """
    return shadow_price * (energy_baseline - energy_residual)


def _as_step_arrays(
    energies: Mapping[EnergyDemandTypeID, Sequence[FloatLike]],
) -> dict[EnergyDemandTypeID, list[FloatArray]]:
    """
    Narrow a whole-timeline energy read to one array per step, for time indexing.

    Parameters
    ----------
    energies
        Energy per energy demand type and step over the whole timeline, GJ/year.

    Returns
    -------
    dict[EnergyDemandTypeID, list[FloatArray]]
        The same arrays, typed as arrays.
    """
    return {
        energy_id: [np.asarray(energy) for energy in steps]
        for energy_id, steps in energies.items()
    }
