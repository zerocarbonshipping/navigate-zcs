# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The most shore-power energy each vessel can take in each of its ports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID
from navigate.util import power_to_energy

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatLike


def calculate_shore_power_limits(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Calculate the most shore-power energy every vessel can take in each of its ports.

    Shore power covers the connected share of the time in port, at the lesser of the
    vessel's shore-power capacity and the electrical load. The limits are in GJ/year.

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
            vessel.expectation.set_shore_power_limit_port(idx, limits)


def _calculate_vessel_limits(vessel: Vessel, idx: int) -> list[FloatLike]:
    """
    Calculate the most shore-power energy a vessel can take in each of its ports.

    Parameters
    ----------
    vessel
        Vessel whose limits are calculated.
    idx
        Current time-step index.

    Returns
    -------
    list[FloatLike]
        Shore-power limit per port over the remaining horizon, in GJ/year.
    """
    expectation = vessel.expectation
    forward = np.s_[idx:]

    capacity = expectation.get_shore_power_capacity(forward)
    times = expectation.get_time_port(forward)
    demands = expectation.get_energy_port(forward)[EnergyDemandID.ELECTRICAL]

    limits = []

    for port, time, demand in zip(vessel.route.ports, times, demands, strict=True):
        share = port.expectation.get_shore_power_connection_share(forward)
        deliverable = power_to_energy(capacity, time)
        limits.append(share * np.minimum(deliverable, demand))

    return limits
