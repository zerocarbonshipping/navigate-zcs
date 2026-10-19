# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer of each regulation's remedial cost and vessel thresholds to its profile."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation


def calculate_regulation_profile(regulation: Regulation, idx: int) -> None:
    """
    Write the regulation's remedial cost and policed-vessel thresholds to its profile.

    Parameters
    ----------
    regulation
        The regulation instance.
    idx
        Current time-step index.
    """
    if not regulation.active:
        return

    profile = regulation.profile

    profile.remedial_cost[idx] = regulation.remedial_cost.get()

    # check_consistency guarantees every policed vessel a threshold
    for vessel_name, threshold in regulation.vessel_threshold.items():
        if regulation.vessel_is_policed(vessel_name) and threshold is not None:
            profile.vessel_threshold[vessel_name][idx] = threshold.get()
