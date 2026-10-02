# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the capital tied in vessels and plants."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_cost

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData


def plot_global_tied_capital(plot_data: PlotData, directory: str) -> None:
    """Plot the capital tied in vessels and plants."""
    dateline = plot_data.dateline

    fig, ax = single_panel()

    profile = plot_data.profile
    vessel_tied_capital = profile.get_vessel_tied_capital()
    plant_tied_capital = profile.get_plant_tied_capital()

    divisor, unit = get_best_unit_cost(
        max(np.max(vessel_tied_capital), np.max(plant_tied_capital)), rate=False
    )

    ax.plot(
        dateline,
        vessel_tied_capital / divisor,
        label="Vessels",
        color=CENTER_COLORS_BLUE[3],
        lw=3,
    )
    ax.plot(
        dateline,
        plant_tied_capital / divisor,
        label="Plants",
        color=CENTER_COLORS_RED[3],
        lw=3,
    )

    ax.set_title("Tied Capital")
    ax.set_ylabel(f"Capital [{unit}]")

    legend = ax.legend(**LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend, y_lim=(0, None))

    save_figure(fig, directory, "global_tied_capital.png")
