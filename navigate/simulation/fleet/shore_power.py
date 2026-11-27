# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Shore-power potential of a technology package, and the limit a port holds it to."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandID
from navigate.util import power_to_energy

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import TechnologyPackage
    from navigate.util.types_ import FloatArray


def calculate_vessel_shore_power_limits(fleets: dict[str, Fleet], idx: int) -> None:
    """
    Calculate the most shore-power energy every vessel can take in each of its ports.

    A vessel's limit in a port is the port's availability times the vessel's
    shore-power potential there, the average over the packages its vessels carry.
    The limits are in GJ/year.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    """
    forward = np.s_[idx:]

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            expectation = vessel.expectation

            potential = expectation.shore_power_potential_port.at[forward]
            limit = calculate_shore_power_limit(vessel, potential, forward)

            expectation.shore_power_limit_port.at[forward] = limit


def calculate_shore_power_potential(
    vessel: Vessel,
    package: TechnologyPackage,
    residual_port: Mapping[EnergyDemandID, FloatArray],
    idx: int | slice,
) -> FloatArray:
    """
    Calculate a package's shore-power potential in each port.

    The potential is the most electrical energy the package can take from shore were
    it connected the whole time in port: the lesser of its shore-power capacity over
    that time and the electrical demand in port with the package.

    Parameters
    ----------
    vessel
        Vessel providing the time in port.
    package
        Technology package holding the shore-power capacity.
    residual_port
        Residual energy in port with the package per energy demand type, the port
        axis first, in GJ/year.
    idx
        Time-step index or slice of the evaluation.

    Returns
    -------
    FloatArray
        Shore-power potential, the port axis first, in GJ/year.
    """
    times_port = np.asarray(vessel.expectation.time_port.at[idx], dtype=float)

    deliverable = power_to_energy(package.shore_power_capacity, times_port)
    electrical = residual_port[EnergyDemandID.ELECTRICAL]

    return np.minimum(deliverable, electrical)


def calculate_shore_power_limit(
    vessel: Vessel, potential: Sequence[FloatArray] | FloatArray, idx: slice
) -> list[FloatArray]:
    """
    Calculate the shore-power limit a potential gives in each port of a vessel.

    Shore power covers the share of the time in port it is available, so the limit
    in a port is the port's availability times the potential there.

    Parameters
    ----------
    vessel
        Vessel calling at the ports.
    potential
        Shore-power potential at each of the time-steps, the port axis first, in
        GJ/year.
    idx
        Time-steps of the evaluation.

    Returns
    -------
    list[FloatArray]
        Shore-power limit at each of the time-steps, the port axis first, in
        GJ/year.
    """
    limit = []

    for p, port in enumerate(vessel.route.ports):
        availability = port.expectation.shore_power_availability[idx]
        limit.append(availability * potential[p])

    return limit
