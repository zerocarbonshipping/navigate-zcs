# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Share each port's fuel supply among vessels by their potential fuel-type demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID, FuelTypeID
from navigate.util import divide_nonzero, unique_list

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatLike


def calculate_fair_share_fuel_supply(
    fleets: dict[str, Fleet],
    fuels: dict[str, Fuel],
    idx: int,
    scope: BunkerScopeID,
) -> None:
    """
    Calculate each vessel's fair share of each port's supply of the given fuels.

    A vessel's fair share is its potential demand for the fuel's type at the port, as a
    fraction of the demand of every vessel calling there, each counted by its
    multiplier. The fair-share iteration of the bunkering starts from these shares.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    fuels
        Fuels whose port supply is shared out, those with a liquid market excluded.
    idx
        Current time-step index.
    scope
        Whether the fair shares are for existing or for expected bunkering.
    """
    port_demand = _calculate_port_demand(fleets, idx, scope)

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            _calculate_vessel_fair_shares(vessel, fuels, port_demand, idx, scope)


def _calculate_port_demand(
    fleets: dict[str, Fleet], idx: int, scope: BunkerScopeID
) -> dict[tuple[str, FuelTypeID], FloatLike]:
    """Calculate each port's potential demand per fuel type, summed over its vessels."""
    horizon = _horizon(idx, scope)
    port_demand: dict[tuple[str, FuelTypeID], FloatLike] = {}

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            expectation = vessel.expectation
            multiplier = fleet.expectation.get_multiplier(vessel.name, scope, horizon)

            # the demand is held per port, so a port called at twice counts once
            for port in unique_list(vessel.route.ports):
                for fuel_type in FuelTypeID:
                    key = (port.name, fuel_type)
                    demand = expectation.get_potential_fuel_type_demand(*key, horizon)
                    port_demand[key] = port_demand.get(key, 0.0) + demand * multiplier

    return port_demand


def _calculate_vessel_fair_shares(
    vessel: Vessel,
    fuels: dict[str, Fuel],
    port_demand: dict[tuple[str, FuelTypeID], FloatLike],
    idx: int,
    scope: BunkerScopeID,
) -> None:
    """Calculate the vessel's fair share of each port's supply of the given fuels."""
    expectation = vessel.expectation
    horizon = _horizon(idx, scope)

    for port in vessel.route.ports:
        for name, fuel in fuels.items():
            if name not in vessel.usable_fuels:
                continue

            key = (port.name, fuel.fuel_type)
            demand = expectation.get_potential_fuel_type_demand(*key, horizon)
            share = divide_nonzero(demand, port_demand[key])

            # existing bunkering evaluates a single time step, where the shares are
            # zero-dimensional arrays
            if scope == BunkerScopeID.EXISTING:
                share = np.float64(share)
                expectation.set_fair_share_fuel_existing(port.name, name, share)
            else:
                expectation.set_fair_share_fuel_expected(idx, port.name, name, share)


def _horizon(idx: int, scope: BunkerScopeID) -> int | slice:
    """Return the steps a scope reads: the current one, or the rest if expected."""
    return idx if scope == BunkerScopeID.EXISTING else np.s_[idx:]
