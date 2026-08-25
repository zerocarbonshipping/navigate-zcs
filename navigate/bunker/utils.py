# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

import navigate.core.enum_ as enum_

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel


def extract_times(vessel: Vessel, idx: int) -> tuple[list, list]:
    """
    Extract time at sea and time in port for a vessel.

    Parameters
    ----------
    vessel
        Vessel for which constraint is being added.
    idx
        Current time-step index.

    Returns
    -------
    tuple[list, list]
        The time at sea and time in port for the vessel (days).
    """

    time_sea = vessel.expectation.get_time_sea(idx)
    time_port = vessel.expectation.get_time_port(idx)

    route = vessel.route
    route_type = route.route_type

    # group to a single cumulative leg
    if route_type == enum_.RouteTypeID.REGIONAL_TRIP:

        sailing_fractions = route.get_voyage_distribution(to_array=True)
        time_sea = np.multiply(sum(time_sea), sailing_fractions)

    return time_sea, time_port
