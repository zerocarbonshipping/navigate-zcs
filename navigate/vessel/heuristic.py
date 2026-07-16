# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.misc import TOLERANCE
from navigate.vessel import Vessel, convert_to_regional_steps
from navigate.vessel.package import Package
from navigate.vessel.saving import calculate_residual_energy

logger = logging.getLogger(__name__)


def get_smoothed_energy_duals_technology(vessel: Vessel
                                         ) -> tuple[dict[EnergyDemandTypeID, list[np.ndarray]],
                                                    dict[EnergyDemandTypePortID, list[np.ndarray]]]:
    """
    Return per-leg shadow-price beliefs amortised over the technology horizon.

    The belief is maintained per (energy-demand-type, leg) by direct EMA
    smoothing of the raw LP duals, so the returned arrays preserve the LP's
    per-leg directional structure with year-to-year volatility damped.

    Parameters
    ----------
    vessel
        Vessel whose beliefs are read via its expectation.

    Returns
    -------
    Tuple of (smoothed_pi_sea, smoothed_pi_port) in the same dict/list/array
    structure as the raw duals.
    """

    expectation = vessel.expectation
    return expectation.get_belief_pi_sea_technology(), expectation.get_belief_pi_port_technology()


def get_smoothed_energy_duals_speed(vessel: Vessel
                                    ) -> tuple[dict[EnergyDemandTypeID, list[np.ndarray]],
                                               dict[EnergyDemandTypePortID, list[np.ndarray]]]:
    """
    Return per-leg shadow-price beliefs amortised over the speed horizon.

    Uses a shorter horizon than the technology variant, matched to the
    timescale of operational speed-management decisions.

    Parameters
    ----------
    vessel
        Vessel whose beliefs are read via its expectation.

    Returns
    -------
    Tuple of (smoothed_pi_sea, smoothed_pi_port) in the same dict/list/array
    structure as the raw duals.
    """

    expectation = vessel.expectation
    return expectation.get_belief_pi_sea_speed(), expectation.get_belief_pi_port_speed()


def calculate_marginal_technology_saving(vessel: Vessel,
                                         package: Package,
                                         idx: slice
                                         ) -> float | np.ndarray:
    """
    Calculate the marginal cost saving from installing a set of technologies.

    The saving is computed by evaluating the dual-variable contribution of changing the
    vessel's energy requirements from the baseline to the residual energy after technology
    impacts. The calculation aggregates savings at sea and in port.

    The baseline energy requirement is defined as the raw energy requirement.
    This is used because the do-nothing-case for installation of technology is defined with NPV=0.
    If using the RHS of the energy conservation equation from the most recent solve of the expected bunker solution,
    this would lead to negative savings for the the lower order technology packages which have lower savings
    than the current average uptake.

    Notice that the use of raw energy as the baseline means that for technology packages with low savings potential
    the evaluation may occur outside the optimal polytype and thus the shadow price may underestimate the impact.

    In debug mode, the function checks whether the residual energy falls outside the
    polytope region where the shadow prices are valid, and logs the fraction of instances
    that extrapolate.

    Parameters
    ----------
    vessel
        Vessel for which the marginal technology saving is evaluated.
    package
        Package containing precomputed savings, powers, and transfer curves.
    idx
        Time-step indeces.

    Returns
    -------
    np.ndarray
        The marginal cost saving per time in `timeline`.
    """

    # calculate the residual energy after installing
    # the technologies on a per-leg basis and convert
    # to regional steps to allow evaluation with
    # shadow prices given on a regoinal-steps basis
    residual_energy_sea, residual_energy_port = calculate_residual_energy(vessel, package, idx)
    residual_energy_sea = convert_to_regional_steps(vessel, residual_energy_sea)

    # use operational energy (prior to technology installation)
    # as a baseline so that the do-nothing case of not
    # installing any technologies corresponds to an
    # NPV=0 business case
    baseline_energy_sea = vessel.expectation.get_regional_operational_energy_sea()
    baseline_energy_port = vessel.expectation.get_operational_energy_port()

    shadow_price_sea, shadow_price_port = get_smoothed_energy_duals_technology(vessel)

    _check_heuristic_consistency(vessel,
                                 residual_energy_sea,
                                 residual_energy_port,
                                 idx,
                                 msg="Technology installation")

    return _calculate_marginal_saving(residual_energy_sea,
                                      residual_energy_port,
                                      baseline_energy_sea,
                                      baseline_energy_port,
                                      shadow_price_sea,
                                      shadow_price_port,
                                      idx)


def calculate_marginal_speed_saving(vessel: Vessel,
                                    residual_energy_sea: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                                    residual_energy_port: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                                    idx: int,
                                    smoothed_duals: tuple[dict[EnergyDemandTypeID, list[np.ndarray]],
                                                          dict[EnergyDemandTypeID, list[np.ndarray]]],
                                    ) -> float | np.ndarray:
    """
    Calculate the marginal cost saving from a speed change.

    The saving is computed by evaluating the dual-variable contribution of changing the
    vessel's energy requirements from the baseline (used in the optimal polytype / bunker
    solution) to the provided residual energy under the speed change. The calculation
    aggregates savings at sea and in port.

    Notice that the `residual_energy_sea` and `residual_energy_port` must be corrected for the impact of current
    technology uptake in order to match the baseline energy requirement.

    In debug mode, the function checks whether the residual energy falls outside the
    polytope region where the shadow prices are valid, and logs the fraction of instances
    that extrapolate.

    Parameters
    ----------
    vessel
        Vessel for which the marginal speed saving is evaluated.
    residual_energy_sea
        Residual energy requirements at sea per energy demand type and leg.
    residual_energy_port
        Residual energy requirements in port per energy demand type and port.
    idx
        Current time-step index.
    smoothed_duals
        Precomputed (shadow_price_sea, shadow_price_port) from
        ``get_smoothed_energy_duals_speed``. Threaded as an argument because
        this function is invoked inside the speed optimisation loop and the
        beliefs do not change across objective evaluations.

    Returns
    -------
    float
        The marginal cost saving.
    """

    residual_energy_sea = convert_to_regional_steps(vessel, residual_energy_sea)

    baseline_energy_sea = vessel.expectation.get_energy_conservation_rhs_sea()
    baseline_energy_port = vessel.expectation.get_energy_conservation_rhs_port()

    shadow_price_sea, shadow_price_port = smoothed_duals

    _check_heuristic_consistency(vessel,
                                 residual_energy_sea,
                                 residual_energy_port,
                                 idx,
                                 msg="Speed management")

    return _calculate_marginal_saving(residual_energy_sea,
                                      residual_energy_port,
                                      baseline_energy_sea,
                                      baseline_energy_port,
                                      shadow_price_sea,
                                      shadow_price_port,
                                      idx)


def _calculate_marginal_saving(residual_energy_sea: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                               residual_energy_port: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                               baseline_energy_sea: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                               baseline_energy_port: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                               shadow_price_sea: dict[EnergyDemandTypeID, list[np.ndarray]],
                               shadow_price_port: dict[EnergyDemandTypeID, list[np.ndarray]],
                               idx: int | slice
                               ) -> float | np.ndarray:
    """
    Calculate total marginal saving by summing savings at sea and in port.

    Parameters
    ----------
    residual_energy_sea
        Residual energy requirements at sea per energy demand type and leg.
    residual_energy_port
        Residual energy requirements in port per energy demand type and port.
    baseline_energy_sea
        Baseline energy requirements at sea per energy demand type and leg.
    baseline_energy_port
        Baseline energy requirements in port per energy demand type and port.
    shadow_price_sea
        Shadow prices at sea, smoothed via the scarcity belief layer.
    shadow_price_port
        Shadow prices in port, smoothed via the scarcity belief layer.
    idx
        Time-step index.

    Returns
    -------
    float | np.ndarray
        Total marginal cost saving (sea + port).
    """

    savings_sea = _iterate_steps(residual_energy_sea, baseline_energy_sea, shadow_price_sea, idx)
    savings_port = _iterate_steps(residual_energy_port, baseline_energy_port, shadow_price_port, idx)

    return savings_sea + savings_port


def _iterate_steps(energies_residual: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                   energies_baseline: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                   shadow_prices: dict[EnergyDemandTypeID, list[np.ndarray]],
                   idx: int | slice) -> float | np.ndarray:
    """
    Accumulate dual-variable savings across all energy demand types and steps.

    For each energy demand type and step, the saving is computed as the shadow price times
    the reduction in energy requirement from baseline to residual. The contributions are
    summed across all types and steps.

    Parameters
    ----------
    energies_residual
        Residual energy requirements per energy demand type and step.
    energies_baseline
        Baseline energy requirements per energy demand type and step.
    shadow_prices
        Shadow prices for changing the energy requirement per energy demand type and step.
    idx
        Time-step indec.

    Returns
    -------
    float | np.ndarray
        Sum of dual-variable savings over all energy types and steps.
    """

    savings = 0.

    for energy_id, energy_residual in energies_residual.items():
        for step, energy_residual_step in enumerate(energy_residual):

            energy_baseline_step = energies_baseline[energy_id][step][idx]
            shadow_price = shadow_prices[energy_id][step][idx]

            savings += _calculate_dual_variable_saving(energy_residual_step,
                                                       energy_baseline_step,
                                                       shadow_price)

    return savings


def _calculate_dual_variable_saving(energy_residual: float | np.ndarray,
                                    energy_baseline: float | np.ndarray,
                                    shadow_price: float | np.ndarray
                                    ) -> float | np.ndarray:
    """
    Calculate the cost saved by changing the energy from the baseline to the residual energy.

    Notice that the saving can be negative in case the residual energy is higher than the baseline. This happens e.g.,
    if speed is increased.

    Parameters
    ----------
    energy_residual
        Residual energy after impact from changed speed or installation of technologies.
    energy_baseline
        Energy required during call to `BunkerAlgorithm` and thus the reference energy for the optimal polytype.
    shadow_price
        Shadow price for changing the energy requirement.

    Returns
    -------
    float | np.ndarray
        The cost saved.
    """

    return shadow_price * (energy_baseline - energy_residual)


def _check_heuristic_consistency(vessel: Vessel,
                                 residual_energy_sea: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                                 residual_energy_port: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                                 idx: int | slice,
                                 msg: str
                                 ) -> None:
    """
    Check how often residual energies fall outside the validity region of the shadow prices.

    The vessel expectation provides lower and upper bounds (polytope bounds) within which
    the shadow prices are considered valid. This function evaluates residual energies at sea
    and in port against these bounds and returns the fraction of instances that lie outside
    the bounds.

    Parameters
    ----------
    vessel
        Vessel providing polytope lower/upper bounds for sea and port energy requirements.
    residual_energy_sea
        Residual energy requirements at sea per energy demand type and step.
    residual_energy_port
        Residual energy requirements in port per energy demand type and step.
    idx
        Time-step index.
    msg
        Additional information to log.
    """

    if logger.getEffectiveLevel() != logging.DEBUG:
        return

    energy_low = vessel.expectation.get_energy_conservation_sarhslow_sea()
    energy_high = vessel.expectation.get_energy_conservation_sarhsup_sea()
    total_sea, outside_sea = _check_polytopes(residual_energy_sea, energy_low, energy_high, idx)

    energy_low = vessel.expectation.get_energy_conservation_sarhslow_port()
    energy_high = vessel.expectation.get_energy_conservation_sarhsup_port()
    total_port, outside_port = _check_polytopes(residual_energy_port, energy_low, energy_high, idx)

    total = total_sea + total_port
    outside = outside_sea + outside_port

    fraction = outside / total

    if fraction > 0.:
        logging.debug(
            f"{vessel}: {msg} evaluation extrapolated outside polytype in : {fraction:.1%} of instances.")


def _check_polytopes(energies_residual: dict[EnergyDemandTypeID, list[float | np.ndarray]],
                     energies_low: dict[EnergyDemandTypeID, list[np.ndarray]],
                     energies_high: dict[EnergyDemandTypeID, list[np.ndarray]],
                     idx: int | slice,
                     ) -> tuple[int, int]:
    """
    Count how many residual-energy instances lie inside vs. outside polytope bounds.

    For each energy demand type and step, the residual energy is compared to the provided
    lower and upper bounds (with numerical tolerance). An instance is considered outside if
    it is below the lower bound or at the upper bound.

    Parameters
    ----------
    energies_residual
        Residual energy requirements per energy demand type and step.
    energies_low
        Lower polytope bounds per energy demand type and step.
    energies_high
        Upper polytope bounds per energy demand type and step.
    idx
        Time-step index.

    Returns
    -------
    tuple[int, int]
        A tuple `(total, outside)` where `total` is the number of evaluated instances and
        `outside` is the number of instances outside the bounds.
    """

    inside = 0
    outside = 0

    for energy_id, energy_residual in energies_residual.items():
        for step, _energy in enumerate(energy_residual):

            energy_low = energies_low[energy_id][step][idx]
            energy_high = energies_high[energy_id][step][idx]

            # check if the residual energy is within the
            # polytope for which the shadow price is valid
            below = np.any(energy_residual < energy_low + TOLERANCE)
            above = np.any(energy_residual > energy_high + TOLERANCE)
            outside = below | above

            inside += np.sum(~outside)
            outside += np.sum(outside)

    return int(inside + outside), outside
