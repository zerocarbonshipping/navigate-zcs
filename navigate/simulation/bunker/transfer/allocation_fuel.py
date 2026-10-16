# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the settled fair-share allocations of fuel to the vessel expectations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_allocation_fuel(alg: BunkerAlgorithm) -> None:
    """
    Transfer each vessel's allocation of the port fuel supply to its expectation.

    The allocation is the one the final solve was constrained by. A port and fuel
    the solve allocated nothing, such as one with an infinite supply, stays at zero.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope != BunkerScopeID.EXISTING:
        return

    # every vessel's allocation restarts from zero, also for a vessel this solve
    # left out and a port and fuel it did not allocate, so none keeps the value of
    # an earlier solve
    for fleet in alg.fleets.values():
        for vessel in fleet.vessels:
            vessel.expectation.reset_allocation_fuel_existing()

    for (v, port_name, f), allocation in alg.allocation_fuel.items():
        vessel = alg.vessels[v]
        vessel.expectation.set_allocation_fuel_existing(port_name, f, allocation)
