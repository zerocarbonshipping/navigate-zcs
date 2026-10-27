# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer of each regulation's remedial cost and vessel thresholds to its results."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.policy._policed import select_policed

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation


def record_regulation_results(regulation: Regulation, idx: int) -> None:
    """
    Write the regulation's remedial cost and policed-vessel thresholds to its results.

    Parameters
    ----------
    regulation
        Regulation whose remedial cost and policed-vessel thresholds are recorded.
    idx
        Current time-step index.
    """
    if not regulation.active:
        return

    results = regulation.results
    thresholds = select_policed(regulation, regulation.vessel_thresholds)

    results.remedial_cost[idx] = regulation.remedial_cost.get()

    # check_consistency guarantees every policed vessel a threshold
    for vessel_name, threshold in thresholds.items():
        if threshold is not None:
            results.vessel_threshold[vessel_name][idx] = threshold.get()
