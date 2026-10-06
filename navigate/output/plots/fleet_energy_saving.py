# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the energy intensity saving per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FLEET_LABEL, extract_label
from navigate.output.plots._layout import trim_axes
from navigate.output.plots._style import LEGEND_OPTIONS

if TYPE_CHECKING:
    from navigate.core.simulation_results import SimulationResults


def plot_fleet_energy_saving(results: SimulationResults, directory: str) -> None:
    """Plot the operational, technology and total energy intensity saving per fleet."""
    dateline = results.dateline
    fleets = results.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    min_saving = 0.0
    max_saving = 0.0

    for ax, fleet in zip(axes, fleets.values(), strict=False):
        fleet_profile = fleet.profile

        operational_saving = (
            fleet_profile.get_operational_energy_intensity_saving() * 100.0
        )
        technology_saving = (
            fleet_profile.get_technology_energy_intensity_saving() * 100.0
        )
        total_saving = fleet_profile.get_energy_intensity_saving() * 100.0

        min_saving = min(
            min_saving,
            np.amin(technology_saving),
            np.amin(operational_saving),
            np.amin(total_saving),
        )
        max_saving = max(
            max_saving,
            np.amax(technology_saving),
            np.amax(operational_saving),
            np.amax(total_saving),
        )

        ax.plot(
            dateline,
            operational_saving,
            label="Operational",
            color=CENTER_COLORS_BLUE[3],
            lw=2,
        )
        ax.plot(
            dateline,
            technology_saving,
            label="Technology",
            color=CENTER_COLORS_RED[3],
            lw=2,
        )
        ax.plot(
            dateline, total_saving, label="Total", color=CENTER_COLORS_GREEN[3], lw=2
        )

        # zero line, as an increased speed gives a negative saving
        ax.plot(dateline, np.zeros_like(dateline, dtype=np.float64), color="k", lw=2)

        ax.set_ylabel("Energy Saving [%]")
        ax.set_title(extract_label(fleet, FLEET_LABEL))

        legend = ax.legend(**LEGEND_OPTIONS)
        format_axes(ax, len(fleets), dateline, legend, y_lim=None)

    trim_axes(axes, len(fleets))

    for ax in axes:
        ax.set_ylim(min_saving - 2.0, max_saving + 2.0)

    save_figure(fig, directory, "fleet_energy_saving.png")
