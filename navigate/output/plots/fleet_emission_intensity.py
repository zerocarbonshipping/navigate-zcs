# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the WTW CO2-equivalent emission intensity per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FLEET_LABEL, extract_label
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData


def plot_fleet_emission_intensity(plot_data: PlotData, directory: str) -> None:
    """Plot the WTW CO2-equivalent emission intensity per fleet."""
    dateline = plot_data.dateline
    fleets = plot_data.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    for ax, fleet in zip(axes, fleets.values(), strict=False):
        intensity = fleet.profile.get_intensity_total_equivalent_wtw()

        ax.plot(dateline, intensity, label="Model", color="k")

        ax.set_ylabel("WTW CO$_2$-eq. intensity [kg/GJ/year]")
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        format_axes(ax, len(fleets), dateline)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, "fleet_emission_intensity.png")
