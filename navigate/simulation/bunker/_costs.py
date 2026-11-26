# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The cost per expense of fuel and shore power, for the LP objective and transfers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import ExpenseID

if TYPE_CHECKING:
    from navigate.core.nodes.port import Port


def calculate_bunker_costs(
    port: Port, vessel_name: str, fuel_name: str, idx: int
) -> dict[ExpenseID, float]:
    """
    Calculate the cost of a ton of fuel a vessel bunkers at a port, per expense.

    Parameters
    ----------
    port
        Port the fuel is bunkered at.
    vessel_name
        Name of the bunkering vessel.
    fuel_name
        Name of the bunkered fuel.
    idx
        Time-step index of the cost.

    Returns
    -------
    dict[ExpenseID, float]
        The port's bunker price and the summed cost of its imposed levies, in
        currency/t.
    """
    key = (vessel_name, port.name, fuel_name)
    levies = port.imposed_levies

    price = port.expectation.bunker_price[fuel_name][idx]
    levy_cost = sum(levy.expectation.cost[key][idx] for levy in levies)

    return {ExpenseID.FUEL: price, ExpenseID.FUEL_LEVY: levy_cost}


def calculate_shore_power_costs(
    port: Port, vessel_name: str, idx: int
) -> dict[ExpenseID, float]:
    """
    Calculate the cost of a GJ of shore power a vessel draws at a port, per expense.

    Parameters
    ----------
    port
        Port the shore power is drawn at.
    vessel_name
        Name of the drawing vessel.
    idx
        Time-step index of the cost.

    Returns
    -------
    dict[ExpenseID, float]
        The port's shore-power price and the summed cost of its imposed levies, in
        currency/GJ.
    """
    key = (vessel_name, port.name)
    levies = port.imposed_levies

    price = port.expectation.shore_power_price[idx]
    levy_cost = sum(levy.expectation.shore_power_cost[key][idx] for levy in levies)

    return {ExpenseID.SHORE_POWER: price, ExpenseID.SHORE_POWER_LEVY: levy_cost}
