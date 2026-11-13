# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Each vessel's shore-power limit per port: the connected share of its potential."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def calculate_shore_power_limits(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Calculate the most shore-power energy every vessel can take in each of its ports.

    Shore power covers the connected share of the time in port, so a vessel's limit in
    a port is the port's connection share of the vessel's shore-power potential there.
    The limits are in GJ/year.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    for fleet in fleets.values():
        for vessel in fleet.vessels:
            limits = _calculate_vessel_limits(vessel, idx)
            vessel.expectation.shore_power_limit_port.at[idx:] = limits


def _calculate_vessel_limits(vessel: Vessel, idx: int) -> list[FloatArray]:
    """
    Calculate the most shore-power energy a vessel can take in each of its ports.

    Each limit is the port's connection share of the vessel's shore-power potential.

    Parameters
    ----------
    vessel
        Vessel whose limits are calculated.
    idx
        Current time-step index.

    Returns
    -------
    list[FloatArray]
        Shore-power limit per port over the remaining horizon, in GJ/year.
    """
    forward = np.s_[idx:]
    potentials = vessel.expectation.shore_power_potential_port.at[forward]

    limits = []

    for port, potential in zip(vessel.route.ports, potentials, strict=True):
        share = port.expectation.shore_power_connection_share[forward]
        limits.append(share * potential)

    return limits
