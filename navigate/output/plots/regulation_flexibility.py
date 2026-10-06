# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the shared and individual compliance of flexible intensity regulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.output.plots._colors import CENTER_COLORS_GREEN
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.output.plots._labels import FUEL_TYPE_COLOR
from navigate.output.plots._style import LEGEND_OPTIONS

if TYPE_CHECKING:
    from matplotlib.lines import Line2D

    from navigate.core.simulation_results import SimulationResults


def plot_regulation_flexibility(results: SimulationResults, directory: str) -> None:
    """Plot the shared and individual compliance of flexible intensity regulations."""
    dateline = results.dateline
    regulations = results.nodes.regulations
    vessels = results.nodes.vessels

    for regulation_name, regulation in regulations.items():
        if regulation.measure != RegulationMeasureID.INTENSITY:
            continue

        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        profile = regulation.profile
        shared_threshold = profile.get_shared_threshold()
        shared_compliance = profile.get_shared_compliance()
        vessel_compliance = {
            vessel_name: compliance
            for vessel_name, compliance in profile.get_vessel_compliance().items()
            if regulation.vessel_is_policed(vessel_name)
        }

        fig, ax = single_panel()

        handles: list[Line2D] = []
        line = ax.plot(dateline, shared_threshold, label="Threshold", color="k", lw=2.0)
        handles.extend(line)
        line = ax.plot(
            dateline,
            shared_compliance,
            label="Compliance",
            color=CENTER_COLORS_GREEN[3],
            lw=2.0,
        )
        handles.extend(line)

        for vessel_name, compliance in vessel_compliance.items():
            color = FUEL_TYPE_COLOR[vessels[vessel_name].primary_fuel_type]
            line = ax.plot(dateline, compliance, color=color, alpha=0.5, lw=1.0)

        handles.extend(line)
        labels = ["Threshold", "Compliance", "Ind. compliance"]
        legend = ax.legend(handles, labels, **LEGEND_OPTIONS)

        ax.set_ylabel("Intensity [kg/GJ]")
        ax.set_ylim(0.0, None)

        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend)

        save_figure(fig, directory, f"regulation_flexibility_{regulation_name}.png")
