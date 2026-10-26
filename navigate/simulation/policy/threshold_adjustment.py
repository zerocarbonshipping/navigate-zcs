# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Adjust the thresholds of non-compliant regulations to the compliance achievable."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.simulation.policy._policed import (
    calculate_achieved_measure,
    normalize_by_measure,
    select_policed,
)
from navigate.simulation.policy.bunkering_inputs import (
    calculate_vessel_allowance,
    calculate_vessel_spend_coefficients,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel

# relative margin on the adjusted thresholds, which keeps their constraints
# non-binding in the re-solve: without it, fair-share redistribution or solver
# numerics can push emissions fractionally above an exact-match threshold and
# reactivate the remedial factor. 1e-4 (0.01 %) absorbs these perturbations and is
# economically negligible.
_THRESHOLD_TOLERANCE = 1e-4


def calculate_adjusted_regulation_thresholds(
    regulations: dict[str, Regulation],
    vessels: dict[str, Vessel],
    multipliers: dict[str, float],
    idx: int,
) -> bool:
    """
    Adjust the thresholds of the regulations a bunkering LP's first solve left unmet.

    A regulation that allows threshold adjustment and is not complied with has its
    threshold raised to the compliance the solve achieved, and the bunkering input
    the threshold enters rewritten at the LP's time step: the allowances, or under
    INTENSITY the spend coefficients. Every active regulation gets its adjusted
    thresholds written: the original where it is complied with, NaN where it allows
    no adjustment.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    multipliers
        Multiplier of each vessel in the bunkering LP, in the LP's order, which the
        sums over the vessels follow.
    idx
        Time-step index of the bunkering LP.

    Returns
    -------
    bool
        True if the LP must be solved again.
    """
    needs_resolve = False

    for regulation in regulations.values():
        if not regulation.active:
            continue

        policed = select_policed(regulation, multipliers)
        vessel_names = policed.keys()

        if not regulation.allow_threshold_adjustment:
            _clear_adjusted_thresholds(regulation, vessel_names, idx)
            continue

        if regulation.scheme == RegulationSchemeID.INDIVIDUAL:
            is_adjusted = _calculate_individual(regulation, vessels, vessel_names, idx)
        else:
            is_adjusted = _calculate_flexible(regulation, vessels, policed, idx)

        needs_resolve = needs_resolve or is_adjusted

    return needs_resolve


def _clear_adjusted_thresholds(
    regulation: Regulation, vessel_names: Iterable[str], idx: int
) -> None:
    """Write NaN as every adjusted threshold of a regulation that adjusts none."""
    expectation = regulation.expectation

    for vessel_name in vessel_names:
        expectation.set_adjusted_vessel_threshold(idx, vessel_name, np.nan)

    expectation.set_adjusted_shared_threshold(idx, np.nan)


def _calculate_individual(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    vessel_names: Iterable[str],
    idx: int,
) -> bool:
    """Calculate each vessel's adjusted threshold; True if any was raised."""
    expectation = regulation.expectation

    is_adjusted = False

    for vessel_name in vessel_names:
        # a compliant vessel keeps its original threshold
        if expectation.get_vessel_remedial_units(vessel_name, idx) <= 0.0:
            threshold = expectation.get_vessel_threshold(vessel_name, idx)
            expectation.set_adjusted_vessel_threshold(idx, vessel_name, threshold)
            continue

        emissions = expectation.get_vessel_emissions(vessel_name, idx)
        measure = calculate_achieved_measure(regulation, vessel_name, idx)

        threshold = _calculate_adjusted_threshold(regulation, emissions, measure)
        expectation.set_adjusted_vessel_threshold(idx, vessel_name, threshold)

        _calculate_adjusted_bunkering_inputs(regulation, vessels[vessel_name], idx)
        is_adjusted = True

    expectation.set_adjusted_shared_threshold(idx, np.nan)

    return is_adjusted


def _calculate_flexible(
    regulation: Regulation,
    vessels: dict[str, Vessel],
    policed_multipliers: dict[str, float],
    idx: int,
) -> bool:
    """Calculate the pool's adjusted vessel and shared thresholds; True if raised."""
    expectation = regulation.expectation

    if expectation.get_pooled_remedial_units(idx) <= 0.0:
        # a compliant regulation keeps the original per-vessel thresholds and has no
        # fleet-level value, so downstream consumers fall back to the per-vessel
        # targets the LP solved against
        for vessel_name in policed_multipliers:
            threshold = expectation.get_vessel_threshold(vessel_name, idx)
            expectation.set_adjusted_vessel_threshold(idx, vessel_name, threshold)

        expectation.set_adjusted_shared_threshold(idx, np.nan)
        return False

    total_emissions = 0.0
    total_measure = 0.0

    for vessel_name, multiplier in policed_multipliers.items():
        emissions = expectation.get_vessel_emissions(vessel_name, idx)
        measure = calculate_achieved_measure(regulation, vessel_name, idx)

        total_emissions += emissions * multiplier
        total_measure += measure * multiplier

        threshold = _calculate_adjusted_threshold(regulation, emissions, measure)
        expectation.set_adjusted_vessel_threshold(idx, vessel_name, threshold)

    shared_threshold = _calculate_adjusted_threshold(
        regulation, total_emissions, total_measure
    )
    expectation.set_adjusted_shared_threshold(idx, shared_threshold)

    for vessel_name in policed_multipliers:
        _calculate_adjusted_bunkering_inputs(regulation, vessels[vessel_name], idx)

    return True


def _calculate_adjusted_bunkering_inputs(
    regulation: Regulation, vessel: Vessel, idx: int
) -> None:
    """Calculate the bunkering input a vessel's adjusted threshold enters, at idx."""
    vessel_name = vessel.name
    expectation = regulation.expectation

    if regulation.measure != RegulationMeasureID.INTENSITY:
        threshold = expectation.get_adjusted_vessel_threshold(vessel_name, idx)
        calculate_vessel_allowance(regulation, vessel_name, threshold, idx)
        return

    # a FLEXIBLE scheme calibrates to the fleet-aggregate intensity, so the
    # re-solved constraint dual carries cross-vessel cost differentiation (dirty
    # vessels are net payers, clean vessels net receivers)
    if regulation.scheme == RegulationSchemeID.FLEXIBLE:
        threshold = expectation.get_adjusted_shared_threshold(idx)
    else:
        threshold = expectation.get_adjusted_vessel_threshold(vessel_name, idx)

    calculate_vessel_spend_coefficients(regulation, vessel, threshold, idx)


def _calculate_adjusted_threshold(
    regulation: Regulation, emissions: float, measure: float
) -> float:
    """
    Calculate the threshold the achieved emissions meet, with the tolerance margin.

    Parameters
    ----------
    regulation
        Regulation whose measure the threshold is stated per.
    emissions
        Achieved emissions of a vessel or the pool, in tons.
    measure
        Achieved measure of the same vessel or pool.

    Returns
    -------
    float
        Adjusted threshold, in the unit of the regulation's threshold.
    """
    achieved = normalize_by_measure(regulation, emissions, measure)
    return achieved * (1.0 + _THRESHOLD_TOLERANCE)
