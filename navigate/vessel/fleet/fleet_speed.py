# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from typing import Callable

import numpy as np

from navigate.core.profiles import FleetProfile
from navigate.vessel import Vessel


def aggregate_speed_profile(assets: list[Vessel],
                            get_multiplier: Callable[[int], float],
                            profile: FleetProfile,
                            idx: int) -> None:
    """
    Aggregate vessel-level speed profiles into fleet-level weighted averages.

    Parameters
    ----------
    assets
        List of vessels in the fleet.
    get_multiplier
        Callable returning the multiplier for vessel index v.
    profile
        Fleet profile to write aggregated results to.
    idx
        Current time-step index.
    """

    time_at_sea = 0.
    reference_speed = 0.
    minimum_speed = 0.
    maximum_speed = 0.
    actual_speed = 0.
    optimal_speed = 0.
    lowest_speed = 0.
    highest_speed = 0.
    reference_multiplier = 0.
    other_multiplier = 0.

    for v, vessel in enumerate(assets):

        vessel_profile = vessel.profile
        multiplier = get_multiplier(v)

        at_sea = vessel_profile.get_time_at_sea(idx)
        reference = vessel_profile.get_reference_speed(idx)
        minimum = vessel_profile.get_minimum_speed(idx)
        maximum = vessel_profile.get_maximum_speed(idx)
        actual = vessel_profile.get_actual_speed(idx)
        optimal = vessel_profile.get_optimal_speed(idx)
        lowest = vessel_profile.get_lowest_speed(idx)
        highest = vessel_profile.get_highest_speed(idx)

        reference_speed += multiplier * reference if not (np.isnan(reference)) else 0.

        if not (np.isnan(minimum) or np.isnan(maximum) or np.isnan(actual)):

            time_at_sea += multiplier * at_sea
            minimum_speed += multiplier * minimum
            maximum_speed += multiplier * maximum
            actual_speed += multiplier * actual
            optimal_speed += multiplier * optimal
            lowest_speed += multiplier * lowest
            highest_speed += multiplier * highest
            other_multiplier += multiplier

        reference_multiplier += multiplier

    profile.set_reference_speed(idx, reference_speed / reference_multiplier)

    if other_multiplier > 0.:
        profile.set_time_at_sea(idx, time_at_sea / other_multiplier)
        profile.set_minimum_speed(idx, minimum_speed / other_multiplier)
        profile.set_maximum_speed(idx, maximum_speed / other_multiplier)
        profile.set_actual_speed(idx, actual_speed / other_multiplier)
        profile.set_optimal_speed(idx, optimal_speed / other_multiplier)
        profile.set_lowest_speed(idx, lowest_speed / other_multiplier)
        profile.set_highest_speed(idx, highest_speed / other_multiplier)
