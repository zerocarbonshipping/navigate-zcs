# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the actual speed of each vessel per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import CENTER_COLORS_GREY
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FLEET_LABEL,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    extract_label,
)
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from navigate.core.simulation_results import SimulationResults


def plot_fleet_speed_per_vessel(results: SimulationResults, directory: str) -> None:
    """Plot the actual speed of each vessel per fleet."""
    dateline = results.dateline
    fleets = results.nodes.fleets
    relevant_fleets = {
        fleet_name: fleet
        for fleet_name, fleet in fleets.items()
        if fleet.allow_speed_management
    }

    if not relevant_fleets:
        return

    fig, axes = subplot_grid(len(relevant_fleets))

    for ax, fleet in zip(axes, relevant_fleets.values(), strict=False):
        profile = fleet.profile
        minimum = profile.get_minimum_speed()
        maximum = profile.get_maximum_speed()

        # there is no speed optimization in the first time-step
        minimum[0] = np.nan
        maximum[0] = np.nan

        ax.fill_between(
            dateline,
            minimum,
            maximum,
            label="Min/Max",
            color=CENTER_COLORS_GREY[1],
            alpha=0.3,
        )

        for vessel in fleet.vessels:
            actual = vessel.profile.get_actual_speed()
            label = FUEL_TYPE_LABEL[vessel.primary_fuel_type]
            color = FUEL_TYPE_COLOR[vessel.primary_fuel_type]

            ax.plot(dateline, actual, label=label, color=color, lw=2.0)

        ax.set_ylabel("Vessel speed [knots]")
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        legend = ax.legend()
        format_axes(ax, len(relevant_fleets), dateline, legend)

    trim_axes(axes, len(relevant_fleets))

    save_figure(fig, directory, "fleet_speed_per_vessel.png")
