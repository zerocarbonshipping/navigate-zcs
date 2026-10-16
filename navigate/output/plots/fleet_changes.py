# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the yearly newbuilds and scrapped vessels per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._aggregate import merge_fleet_newbuilds, merge_fleet_scrap
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


def plot_fleet_changes(results: SimulationResults, directory: Path) -> None:
    """Plot the yearly newbuilds and scrapped vessels per fleet."""
    dateline = results.dateline
    fleets = results.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    for ax, fleet in zip(axes, fleets.values(), strict=False):
        scraps, scrap_labels, scrap_colors, title = merge_fleet_scrap(dateline, fleet)
        builds, build_labels, build_colors, _ = merge_fleet_newbuilds(dateline, fleet)

        plot_stack_with_lines(ax, dateline, scraps, scrap_labels, scrap_colors)
        plot_stack_with_lines(ax, dateline, builds, build_labels, build_colors)

        ax.plot([dateline[0], dateline[-1]], [0.0, 0.0], c="k", lw=2)

        ax.set_ylabel("# vessels/year")
        ax.set_title(title)
        format_axes(ax, len(fleets), dateline, y_lim=(None, None))

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, "fleet_changes.png")
