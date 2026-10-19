# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the computational time of the run by phase, per step and cumulative."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import TimingID
from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_GREY,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def _plot_computational_performance(
    results: SimulationResults, directory: Path, cumulative: bool
) -> None:
    dateline = results.dateline
    seconds = results.profile.computational_time

    fig, ax = single_panel()

    # one hue per domain: the bunkering LP, the fleet, fuel supply, policy and the rest
    styles = {
        TimingID.LP_BUILD: ("LP build", CENTER_COLORS_BLUE[2]),
        TimingID.LP_SOLVE: ("LP solve", CENTER_COLORS_BLUE[4]),
        TimingID.LP_TRANSFER: ("LP transfer", CENTER_COLORS_BLUE[6]),
        TimingID.FLEET_EVOLUTION: ("Fleet evolution", CENTER_COLORS_YELLOW[2]),
        TimingID.SPEED_MANAGEMENT: ("Speed management", CENTER_COLORS_YELLOW[4]),
        TimingID.TECHNOLOGY_INSTALLATION: ("Technology", CENTER_COLORS_YELLOW[6]),
        TimingID.PLANT_PRODUCTION: ("Plant production", CENTER_COLORS_GREEN[3]),
        TimingID.PRODUCER_EVOLUTION: ("Producer evolution", CENTER_COLORS_GREEN[5]),
        TimingID.POLICY: ("Policy", CENTER_COLORS_RED[4]),
        TimingID.OTHER: ("Other", CENTER_COLORS_GREY[3]),
    }

    values = [seconds[phase] for phase in styles]
    labels = [label for label, _ in styles.values()]
    colors = [color for _, color in styles.values()]

    if cumulative:
        values = [np.cumsum(value) for value in values]
        ax.set_ylabel("Cumulative computational time [s]")
        suffix = "_cumulative"
    else:
        ax.set_ylabel("Computational time per step [s]")
        suffix = ""

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)
    ax.plot(dateline, np.sum(values, axis=0), color="k", ls="--", lw=2.0)

    legend = ax.legend(stack[::-1], labels[::-1], ncol=2, **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, f"computational_performance{suffix}.png")


def plot_computational_performance(results: SimulationResults, directory: Path) -> None:
    """Plot the computational time per time step by run phase."""
    _plot_computational_performance(results, directory, cumulative=False)


def plot_computational_performance_cumulative(
    results: SimulationResults, directory: Path
) -> None:
    """Plot the cumulative computational time by run phase."""
    _plot_computational_performance(results, directory, cumulative=True)
