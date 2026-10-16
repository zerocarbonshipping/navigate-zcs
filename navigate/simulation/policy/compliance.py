# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The allowances and compliance of each regulation and its policed vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel


def calculate_regulation_allowances(
    regulations: dict[str, Regulation], vessels: dict[str, Vessel], idx: int
) -> None:
    """
    Calculate the allowance of every policed vessel under each active regulation.

    A vessel's allowance, its threshold times its measure, is the right-hand side it
    contributes to its threshold constraint in the bunkering LP. Under INTENSITY the
    measure is zero, and so is the allowance: the threshold enters the spend
    coefficients instead.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    horizon = np.s_[idx:]

    for regulation in regulations.values():
        if not regulation.active:
            continue

        expectation = regulation.expectation

        for vessel_name in vessels:
            if not regulation.vessel_is_policed(vessel_name):
                continue

            threshold = expectation.get_vessel_threshold(vessel_name, horizon)
            measure = expectation.get_vessel_measure(vessel_name, horizon)
            expectation.set_vessel_allowance(idx, vessel_name, threshold * measure)
