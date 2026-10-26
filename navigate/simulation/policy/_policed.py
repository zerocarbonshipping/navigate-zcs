# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""A regulation's policed vessels and their accounts in a bunkering LP."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.util import TON_TO_KG, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation


class VesselAccount(NamedTuple):
    """A policed vessel's regulated emissions, measure and allowance at a time step."""

    emissions: float
    measure: float
    allowance: float


def select_policed[T](regulation: Regulation, items: dict[str, T]) -> dict[str, T]:
    """
    Select the entries of the vessels a regulation polices.

    Parameters
    ----------
    regulation
        Regulation whose policed vessels are selected.
    items
        Entries keyed by vessel name, in the order the sums over the vessels follow.

    Returns
    -------
    dict[str, T]
        Entries of the policed vessels, in the order of `items`.
    """
    policed = {}

    for vessel_name, value in items.items():
        if regulation.vessel_is_policed(vessel_name):
            policed[vessel_name] = value

    return policed


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
    measure = calculate_achieved_measure(regulation, vessel_name, idx)

    if regulation.scheme == RegulationSchemeID.FLEXIBLE:
        threshold = expectation.get_adjusted_shared_threshold(idx)
    else:
        threshold = expectation.get_adjusted_vessel_threshold(vessel_name, idx)

    if np.isnan(threshold):
        threshold = expectation.get_vessel_threshold(vessel_name, idx)

    return VesselAccount(emissions, measure, threshold * measure)


def calculate_achieved_measure(
    regulation: Regulation, vessel_name: str, idx: int
) -> float:
    """
    Calculate a policed vessel's measure in the bunkering LP of a time step.

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
    float
        Measure of the vessel, which turns its threshold into its allowance.
    """
    expectation = regulation.expectation

    # the energy, and with it the measure, of an intensity regulation is a result of
    # the bunkering
    if regulation.measure == RegulationMeasureID.INTENSITY:
        return expectation.get_vessel_energy(vessel_name, idx) / TON_TO_KG

    return expectation.get_vessel_measure(vessel_name, idx)


def normalize_by_measure(regulation: Regulation, value: float, measure: float) -> float:
    """
    Normalize a regulated value by its measure; ABSOLUTE passes it through.

    Parameters
    ----------
    regulation
        Regulation whose measure the value is normalized by.
    value
        Emissions or allowance of a vessel or a pool, in tons.
    measure
        Measure of the same vessel or pool.

    Returns
    -------
    float
        Value per unit of measure, in the unit of the regulation's threshold.
    """
    if regulation.measure == RegulationMeasureID.ABSOLUTE:
        return value

    # the measure is zero for a vessel that spent no energy or has no port in the
    # jurisdiction, and for a pool without policed vessels
    return np.float64(divide_nonzero(value, measure))
