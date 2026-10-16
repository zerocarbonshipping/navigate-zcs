# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Share each port's fuel supply among vessels by their potential fuel-type demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID, FuelTypeID
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_fair_share_fuel_supply(
    fleets: dict[str, Fleet],
    fuels: dict[str, Fuel],
    idx: int,
    scope: BunkerScopeID,
) -> None:
    """
    Calculate fair-share fuel supply from each port for every vessel in the simulation.

    Used as a starting guess for the fair-share of fuel supply during existing
    bunkering.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    fuels
        All fuels in the simulation.
    idx
        Current time-step index.
    scope
        Whether the fair shares are for existing or for expected bunkering.
    """
    fair_share, vessels = _calculate_demand_based_fair_share_fuel_supply(
        fleets, idx, scope
    )

    for v, vessel in vessels.items():
        for port in vessel.route.ports:
            p = port.name

            for f, fuel in fuels.items():
                if f not in vessel.usable_fuels:
                    continue

                fuel_type = fuel.fuel_type

                # existing bunkering evaluates a single time step, where the shares
                # are zero-dimensional arrays
                if scope == BunkerScopeID.EXISTING:
                    vessel.expectation.set_fair_share_fuel_existing(
                        p, f, np.float64(fair_share[(v, p, fuel_type)])
                    )
                else:
                    vessel.expectation.set_fair_share_fuel_expected(
                        idx, p, f, fair_share[(v, p, fuel_type)]
                    )


def _calculate_demand_based_fair_share_fuel_supply(
    fleets: dict[str, Fleet],
    idx: int,
    scope: BunkerScopeID,
) -> tuple[dict[tuple[str, str, FuelTypeID], FloatArray], dict[str, Vessel]]:
    """
    Calculate the fair-share fuel type supply from each port for every vessel.

    Parameters
    ----------
    fleets
        All fleets in the simulation.
    idx
        Current time-step index.
    scope
        Whether the fair shares are for existing or for expected bunkering; expected
        bunkering evaluates the remaining timeline.

    Returns
    -------
    tuple[dict[tuple[str, str, FuelTypeID], FloatArray], dict[str, Vessel]]
        Fair share of the fuel type supply per (vessel, port, fuel type), and every
        vessel in the simulation by name.
    """
    time_index = idx if scope == BunkerScopeID.EXISTING else np.s_[idx:]

    vessels: dict[str, Vessel] = {}
    multipliers: dict[str, FloatLike] = {}

    for fleet in fleets.values():
        for vessel in fleet.vessels:
            v = vessel.name

            vessels[v] = vessel
            multipliers[v] = fleet.expectation.get_multiplier(v, scope, time_index)

    all_demand: dict[tuple[str, str, FuelTypeID], FloatLike] = {}
    for v, vessel in vessels.items():
        expectation = vessel.expectation

        for port in vessel.route.ports:
            p = port.name

            for ft in FuelTypeID:
                demand = expectation.get_potential_fuel_type_demand(p, ft, time_index)
                all_demand[(v, p, ft)] = demand

    # the demand is held vessel by vessel, so each port total adds up in vessel order
    total_demand: dict[tuple[str, FuelTypeID], FloatLike] = {}
    for (v, p, ft), demand in all_demand.items():
        total = total_demand.get((p, ft), 0.0)
        total_demand[(p, ft)] = total + demand * multipliers[v]

    fair_share = {}
    for v, vessel in vessels.items():
        for port in vessel.route.ports:
            p = port.name

            for ft in FuelTypeID:
                if ft not in vessel.usable_fuel_types:
                    continue

                share = divide_nonzero(all_demand[(v, p, ft)], total_demand[(p, ft)])
                fair_share[(v, p, ft)] = share

    return fair_share, vessels
