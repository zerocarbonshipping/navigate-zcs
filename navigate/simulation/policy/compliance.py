# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The allowances and compliance of each regulation and its policed vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.simulation.policy._policed import (
    calculate_vessel_account,
    normalize_by_measure,
    select_policed,
)

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation


def calculate_regulation_compliance(
    regulations: dict[str, Regulation], multipliers: dict[str, float], idx: int
) -> None:
    """
    Calculate the compliance, allowance and units of each active regulation.

    Each is read from the existing bunkering LP and written, with the adjusted
    thresholds, to the regulation's results, per policed vessel and shared across them.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    multipliers
        Multiplier of each vessel in the existing bunkering LP, in the LP's order,
        which the sums over the vessels follow.
    idx
        Current time-step index.
    """
    for regulation in regulations.values():
        if not regulation.active:
            continue

        _calculate_compliance_results(regulation, multipliers, idx)
        _record_adjusted_thresholds(regulation, multipliers, idx)


def _calculate_compliance_results(
    regulation: Regulation, multipliers: dict[str, float], idx: int
) -> None:
    """Write the vessel and shared compliance, allowance and units to the results."""
    results = regulation.results

    total_emissions = 0.0
    total_measure = 0.0
    total_allowance = 0.0

    for vessel_name, multiplier in select_policed(regulation, multipliers).items():
        account = calculate_vessel_account(regulation, vessel_name, idx)

        total_emissions += multiplier * account.emissions
        total_measure += multiplier * account.measure
        total_allowance += multiplier * account.allowance

        # a vessel with no port in the jurisdiction has a zero measure
        if account.measure <= 0.0:
            continue

        vessel_compliance = account.emissions / account.measure
        results.vessel_compliance[vessel_name][idx] = vessel_compliance
        results.vessel_allowance[vessel_name][idx] = account.allowance
        results.vessel_units[vessel_name][idx] = account.emissions

    results.shared_allowance[idx] = total_allowance
    results.shared_units[idx] = total_emissions

    # shared compliance and threshold only make sense for absolute emissions and
    # energy intensity: transport-based intensities need not share a unit
    if regulation.measure not in (
        RegulationMeasureID.ABSOLUTE,
        RegulationMeasureID.INTENSITY,
    ):
        return

    compliance = normalize_by_measure(regulation, total_emissions, total_measure)
    results.shared_compliance[idx] = compliance

    # the fleet-level effective target of a flexible regulation: the measure-weighted
    # mean of the per-vessel thresholds, equal to the uniform value when the
    # thresholds are assigned via a wildcard
    if regulation.scheme == RegulationSchemeID.FLEXIBLE:
        threshold = normalize_by_measure(regulation, total_allowance, total_measure)
        results.shared_threshold[idx] = threshold


def _record_adjusted_thresholds(
    regulation: Regulation, multipliers: dict[str, float], idx: int
) -> None:
    """
    Write the adjusted thresholds to the regulation's results.

    Only the vessels of the LP are read: the slot of any other vessel may hold the
    result of an earlier LP.
    """
    expectation = regulation.expectation
    results = regulation.results

    for vessel_name in select_policed(regulation, multipliers):
        threshold = expectation.get_adjusted_vessel_threshold(vessel_name, idx)
        if not np.isnan(threshold):
            results.adjusted_vessel_threshold[vessel_name][idx] = threshold

    shared_threshold = expectation.get_adjusted_shared_threshold(idx)
    if not np.isnan(shared_threshold):
        results.adjusted_shared_threshold[idx] = shared_threshold
