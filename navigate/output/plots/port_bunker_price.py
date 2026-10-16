# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the bunker price of each fuel, one figure per port."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._aggregate import merge_fuel_costs
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def plot_port_bunker_price(results: SimulationResults, directory: Path) -> None:
    """Plot the bunker price of each fuel, one figure per port."""
    dateline = results.dateline
    fuels = results.nodes.fuels
    ports = results.nodes.ports

    for port_name, port in ports.items():
        bunker_price = port.profile.get_bunker_price()
        fuel_costs = {
            fuel.name: bunker_price[fuel.name] / fuel.lower_heating_value.get()
            for fuel in fuels.values()
        }

        # a zero price marks a time step the fuel is unavailable
        fuel_costs = {
            fuel_name: np.where(cost == 0.0, np.nan, cost)
            for fuel_name, cost in fuel_costs.items()
        }

        values, colors, titles = merge_fuel_costs(fuel_costs, fuels)

        if not titles:
            continue

        fig, axes = subplot_grid(len(titles), sharey=True)

        min_value = 0.0

        for ax, group_values, group_colors, title in zip(
            axes, values, colors, titles, strict=False
        ):
            for value, color in zip(group_values, group_colors, strict=True):
                ax.plot(dateline, value, color=color, lw=2.5)
                min_value = min(min_value, np.amin(value))

            ax.set_ylabel("Bunker price [USD/GJ]")
            ax.set_title(title, color="k")
            format_axes(ax, len(values), dateline, y_lim=None)

        if min_value == 0.0:
            for ax in axes:
                ax.set_ylim(0.0, None)

        trim_axes(axes, len(titles))

        save_figure(fig, directory, f"port_bunker_price_{port_name}.png")
