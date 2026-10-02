# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the global WTW CO2-equivalent emission intensity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData


def plot_global_emission_intensity(plot_data: PlotData, directory: str) -> None:
    """Plot the global WTW CO2-equivalent emission intensity."""
    dateline = plot_data.dateline

    fig, ax = single_panel()

    intensity = plot_data.profile.get_intensity_total_equivalent_wtw()

    ax.plot(dateline, intensity, color="k")

    ax.set_ylabel("WTW CO$_2$-eq. intensity [kg/GJ/year]")
    format_axes(ax, 1, dateline)

    save_figure(fig, directory, "global_emission_intensity.png")
