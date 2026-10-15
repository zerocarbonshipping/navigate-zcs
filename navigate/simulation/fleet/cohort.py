# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The vessel cohorts of a fleet: their initial split by age, ageing and count."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.increment import VesselIncrement
from navigate.simulation.economics.cohort import discretize_initial_cohorts
from navigate.util import YEAR

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel


def define_initial_cohorts(fleet: Fleet) -> None:
    """
    Split each vessel type's share of the initial vessels into cohorts by age.

    Parameters
    ----------
    fleet
        Fleet to define the initial cohorts for, with its initial split defined.
    """
    distributions = fleet.initial_age_distribution
    initial_vessels = fleet.initial_vessels.get()
    n_packages = fleet.get_number_of_packages()

    for v, vessel in enumerate(fleet.assets):
        distribution = distributions[v] if distributions else None
        lifetime = _get_initial_lifetime(fleet, vessel)
        total = fleet.initial_split[v] * initial_vessels
        cohorts = discretize_initial_cohorts(distribution, lifetime, total)

        increments = []
        for age, span, multiplier in cohorts:
            increment = VesselIncrement(
                multiplier=multiplier,
                age=age,
                age_span=span,
                package_uptake=np.zeros(n_packages),
            )
            increments.append(increment)

        # the oldest cohort holds the baseline of partial age-based scrapping
        if increments:
            increments[0].baseline = increments[0].multiplier

        fleet.increments.append(increments)


def age_fleet_cohorts(fleet: Fleet, time_step: float) -> None:
    """
    Age every vessel cohort of the fleet by the time step.

    Parameters
    ----------
    fleet
        Fleet to age.
    time_step
        Time-step size, in days.
    """
    dt = time_step / YEAR

    for increments in fleet.increments:
        for increment in increments:
            increment.age += dt


def get_multiplier(fleet: Fleet, index: int) -> float:
    """
    Return the number of vessels of one vessel type, summed over its cohorts.

    Parameters
    ----------
    fleet
        Fleet holding the vessel type.
    index
        Index of the vessel type in the fleet.

    Returns
    -------
    float
        Number of vessels of the vessel type.
    """
    return sum(increment.multiplier for increment in fleet.increments[index])


def get_multipliers(fleet: Fleet) -> list[float]:
    """
    Return the number of vessels of each vessel type of the fleet.

    Parameters
    ----------
    fleet
        Fleet to count.

    Returns
    -------
    list[float]
        Number of vessels of each vessel type.
    """
    return [get_multiplier(fleet, v) for v in range(len(fleet.increments))]


def _get_initial_lifetime(fleet: Fleet, vessel: Vessel) -> float:
    """Return the lifetime the initial vessels of a type are spread over, in years."""
    lifetime = vessel.lifetime.get()

    if fleet.fixed_scrap_rate is None:
        return lifetime

    # a fixed scrap rate scraps the existing vessels within 1 / rate years
    scrap_rate = fleet.fixed_scrap_rate.get()
    return min(lifetime, 1.0 / scrap_rate) if scrap_rate > 0.0 else lifetime
