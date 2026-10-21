# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The allowances and compliance of each regulation and its policed vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.util import TON_TO_KG, divide_nonzero

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.regulation import Regulation


class VesselAccount(NamedTuple):
    """A policed vessel's regulated emissions, measure and allowance at a time step."""

    emissions: float
    measure: float
    allowance: float


def calculate_vessel_account(
    regulation: Regulation, vessel_name: str, idx: int
) -> VesselAccount:
    """
    Calculate a policed vessel's account from the bunkering LP of a time step.

    The allowance holds the vessel to its adjusted threshold, where one was
    adjusted, so that non-compliance and surplus are measured against the target
    the fleet actually trades against; under FLEXIBLE, every vessel is held to the
    shared adjusted threshold.

    Parameters
    ----------
    regulation
        Regulation policing the vessel.
    vessel_name
        Name of the vessel, which entered the bunkering LP.
    idx
        Time-step index of the bunkering LP.

    Returns
    -------
    VesselAccount
        Regulated emissions, measure and allowance of the vessel.
    """
    expectation = regulation.expectation

    emissions = expectation.get_vessel_emissions(vessel_name, idx)

    if regulation.measure == RegulationMeasureID.INTENSITY:
        # the energy, and with it the measure, of an intensity regulation is a
        # result of the bunkering
        measure = expectation.get_vessel_energy(vessel_name, idx) / TON_TO_KG
    else:
        measure = expectation.get_vessel_measure(vessel_name, idx)

    if regulation.scheme == RegulationSchemeID.FLEXIBLE:
        threshold = expectation.get_adjusted_shared_threshold(idx)
    else:
        threshold = expectation.get_adjusted_vessel_threshold(vessel_name, idx)

    if np.isnan(threshold):
        threshold = expectation.get_vessel_threshold(vessel_name, idx)

    return VesselAccount(emissions, measure, threshold * measure)


def calculate_regulation_compliance(
    regulations: dict[str, Regulation], multipliers: dict[str, float], idx: int
) -> None:
    """
    Calculate the compliance, allowance and units of each active regulation.

    Read from the existing bunkering LP, they go to the regulation's results, per
    policed vessel and shared across them, with the adjusted thresholds.

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
        _calculate_adjusted_threshold_results(regulation, multipliers, idx)


def _calculate_compliance_results(
    regulation: Regulation, multipliers: dict[str, float], idx: int
) -> None:
    """Write the vessel and shared compliance, allowance and units to the results."""
    results = regulation.results

    total_emissions = 0.0
    total_measure = 0.0
    total_allowance = 0.0

    for vessel_name, multiplier in multipliers.items():
        if not regulation.vessel_is_policed(vessel_name):
            continue

        account = calculate_vessel_account(regulation, vessel_name, idx)

        total_emissions += multiplier * account.emissions
        total_measure += multiplier * account.measure
        total_allowance += multiplier * account.allowance

        # a vessel with no port in the jurisdiction has a zero measure
        if not (account.measure > 0.0):
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

    compliance = _normalize_by_measure(regulation, total_emissions, total_measure)
    results.shared_compliance[idx] = compliance

    # the fleet-level effective target of a flexible regulation: the measure-weighted
    # mean of the per-vessel thresholds, equal to the uniform value when the
    # thresholds are assigned via a wildcard
    if regulation.scheme == RegulationSchemeID.FLEXIBLE:
        threshold = _normalize_by_measure(regulation, total_allowance, total_measure)
        results.shared_threshold[idx] = threshold


def _calculate_adjusted_threshold_results(
    regulation: Regulation, vessel_names: Iterable[str], idx: int
) -> None:
    """
    Write the adjusted thresholds to the regulation's results.

    Only the vessels of the LP are read: the slot of any other vessel may hold the
    result of an earlier LP.
    """
    expectation = regulation.expectation
    results = regulation.results

    for vessel_name in vessel_names:
        if not regulation.vessel_is_policed(vessel_name):
            continue

        threshold = expectation.get_adjusted_vessel_threshold(vessel_name, idx)
        if not np.isnan(threshold):
            results.adjusted_vessel_threshold[vessel_name][idx] = threshold

    shared_threshold = expectation.get_adjusted_shared_threshold(idx)
    if not np.isnan(shared_threshold):
        results.adjusted_shared_threshold[idx] = shared_threshold


def _normalize_by_measure(
    regulation: Regulation, value: float, total_measure: float
) -> float:
    """Normalize a fleet aggregate by the pooled measure; ABSOLUTE passes through."""
    if regulation.measure == RegulationMeasureID.ABSOLUTE:
        return value

    # the pooled measure is zero when no vessel is policed
    return np.float64(divide_nonzero(value, total_measure))
