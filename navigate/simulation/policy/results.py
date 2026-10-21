# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer of each regulation's remedial cost and vessel thresholds to its results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation


def record_regulation_results(regulation: Regulation, idx: int) -> None:
    """
    Write the regulation's remedial cost and policed-vessel thresholds to its results.

    Parameters
    ----------
    regulation
        The regulation instance.
    idx
        Current time-step index.
    """
    if not regulation.active:
        return

    results = regulation.results

    results.remedial_cost[idx] = regulation.remedial_cost.get()

    # check_consistency guarantees every policed vessel a threshold
    for vessel_name, threshold in regulation.vessel_threshold.items():
        if regulation.vessel_is_policed(vessel_name) and threshold is not None:
            results.vessel_threshold[vessel_name][idx] = threshold.get()
