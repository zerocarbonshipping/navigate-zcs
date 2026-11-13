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
    regulations: dict[str, Regulation], counts: dict[str, float], idx: int
) -> None:
    """
    Calculate the compliance, allowance and units of each active regulation.

    Each is read from the existing bunkering LP and written, with the adjusted
    thresholds, to the regulation's results, per policed vessel and shared across them.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    counts
        Count of each vessel type in the existing bunkering LP, in the LP's order,
        which the sums over the vessels follow.
    idx
        Time-step index of the bunkering LP.
    """
    for regulation in regulations.values():
        if not regulation.active:
            continue

        _record_compliance(regulation, counts, idx)
        _record_adjusted_thresholds(regulation, counts, idx)


def _record_compliance(
    regulation: Regulation, counts: dict[str, float], idx: int
) -> None:
    """Write the vessel and shared compliance, allowance and units to the results."""
    results = regulation.results

    total_emissions = 0.0
    total_measure = 0.0
    total_allowance = 0.0

    for vessel_name, count in select_policed(regulation, counts).items():
        account = calculate_vessel_account(regulation, vessel_name, idx)

        total_emissions += count * account.emissions
        total_measure += count * account.measure
        total_allowance += count * account.allowance

        # a vessel that spent no energy under INTENSITY, or has no regulated cargo
        # miles under a transport measure, has a zero measure
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
    if regulation.measure in (
        RegulationMeasureID.TRANSPORT,
        RegulationMeasureID.TRANSPORT_NOMINAL,
    ):
        return

    compliance = normalize_by_measure(regulation, total_emissions, total_measure)
    results.shared_compliance[idx] = compliance

    # the fleet-level effective target of a flexible regulation: the measure-weighted
    # mean of the per-vessel thresholds, equal to the uniform value when the
    # thresholds are assigned via a wildcard; under ABSOLUTE their weighted sum
    if regulation.scheme == RegulationSchemeID.FLEXIBLE:
        threshold = normalize_by_measure(regulation, total_allowance, total_measure)
        results.shared_threshold[idx] = threshold


def _record_adjusted_thresholds(
    regulation: Regulation, counts: dict[str, float], idx: int
) -> None:
    """
    Write the adjusted thresholds to the regulation's results.

    Only the vessels of the LP are read: the slot of any other vessel may hold the
    result of an earlier LP.
    """
    expectation = regulation.expectation
    results = regulation.results

    for vessel_name in select_policed(regulation, counts):
        threshold = expectation.adjusted_vessel_threshold[vessel_name][idx]
        if not np.isnan(threshold):
            results.adjusted_vessel_threshold[vessel_name][idx] = threshold

    shared_threshold = expectation.adjusted_shared_threshold[idx]
    if not np.isnan(shared_threshold):
        results.adjusted_shared_threshold[idx] = shared_threshold
