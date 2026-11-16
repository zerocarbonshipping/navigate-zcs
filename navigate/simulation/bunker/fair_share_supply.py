# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Share each port's fuel supply among vessels by their potential fuel-type demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID, FuelTypeID
from navigate.simulation.bunker._indices import get_scope_steps
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker._indices import ScopeSteps
    from navigate.util.types_ import FloatLike


def calculate_fair_share_fuel_supply(
    fleets: dict[str, Fleet], idx: int, scope: BunkerScopeID
) -> None:
    """
    Calculate each vessel's fair share of each port's supply of the fuels it can use.

    A vessel's fair share is its potential demand for the fuel's type at the port, as a
    fraction of the demand of every vessel calling there, each weighted by its count.
    The fair-share iteration of the bunkering starts from these shares.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    scope
        Whether the fair shares are for existing or for expected bunkering.
    """
    steps = get_scope_steps(idx, scope)
    port_demand = _calculate_port_demand(fleets, steps, scope)

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            _calculate_vessel_fair_shares(vessel, port_demand, idx, steps, scope)


def _calculate_port_demand(
    fleets: dict[str, Fleet], steps: ScopeSteps, scope: BunkerScopeID
) -> dict[tuple[str, FuelTypeID], FloatLike]:
    """Calculate each port's potential demand per fuel type, summed over its vessels."""
    port_demand: dict[tuple[str, FuelTypeID], FloatLike] = {}

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            expectation = vessel.expectation
            count = fleet.expectation.count[vessel.name, scope][steps]

            # the demand is held per port, so a port called at twice counts once
            for port in vessel.route.distinct_ports:
                for fuel_type in FuelTypeID:
                    key = (port.name, fuel_type)
                    demand = expectation.potential_fuel_type_demand[key][steps]
                    port_demand[key] = port_demand.get(key, 0.0) + demand * count

    return port_demand


def _calculate_vessel_fair_shares(
    vessel: Vessel,
    port_demand: dict[tuple[str, FuelTypeID], FloatLike],
    idx: int,
    steps: ScopeSteps,
    scope: BunkerScopeID,
) -> None:
    """Calculate the vessel's fair share of each port's supply of its usable fuels."""
    expectation = vessel.expectation

    for port in vessel.route.distinct_ports:
        for name, fuel in vessel.usable_fuels.items():
            key = (port.name, fuel.fuel_type)
            demand = expectation.potential_fuel_type_demand[key][steps]
            share = divide_nonzero(demand, port_demand[key])

            # existing bunkering evaluates a single time-step, where the shares are
            # zero-dimensional arrays
            if scope == BunkerScopeID.EXISTING:
                expectation.fair_share_fuel_existing[port.name, name] = float(share)
            else:
                expectation.fair_share_fuel_expected[port.name, name][idx:] = share
