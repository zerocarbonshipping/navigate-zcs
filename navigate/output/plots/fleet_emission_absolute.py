# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the WTW CO2-equivalent emissions per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FLEET_LABEL, extract_label
from navigate.output.plots._layout import trim_axes
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_mass

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def plot_fleet_emission_absolute(results: SimulationResults, directory: Path) -> None:
    """Plot the WTW CO2-equivalent emissions per fleet."""
    dateline = results.dateline
    fleets = results.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    for ax, fleet in zip(axes, fleets.values(), strict=False):
        wtw = fleet.profile.get_total_equivalent_wtw()

        divisor, unit = get_best_unit_mass(wtw.max())
        wtw /= divisor

        ax.plot(dateline, wtw, label="WTW", color="k")

        ax.set_ylabel(f"WTW CO$_2$-eq. [{unit}]")
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        legend = ax.legend(**LEGEND_OPTIONS)
        format_axes(ax, len(fleets), dateline, legend)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, "fleet_emission_absolute.png")
