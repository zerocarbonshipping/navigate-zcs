# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the number of existing vessels per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._aggregate import merge_fleet_evolution
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def plot_fleet_evolution(results: SimulationResults, directory: Path) -> None:
    """Plot the number of existing vessels per fleet, by fuel type."""
    dateline = results.dateline
    fleets = results.nodes.fleets

    fig, axes = subplot_grid(len(fleets), sharex=True)

    for ax, fleet in zip(axes, fleets.values(), strict=False):
        values, labels, colors, title = merge_fleet_evolution(dateline, fleet)

        plot_stack_with_lines(ax, dateline, values, labels, colors)

        ax.set_ylabel("Number of vessels")
        ax.set_title(title)
        format_axes(ax, len(fleets), dateline)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, "fleet_evolution.png")
