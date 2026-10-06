# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the computational time of the run by phase, per step and cumulative."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._aggregate import to_cumulative
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
    from navigate.core.simulation_results import SimulationResults


def _plot_computational_performance(
    results: SimulationResults, directory: str, cumulative: bool
) -> None:
    dateline = results.dateline
    profile = results.profile

    fig, ax = single_panel()

    # per-step times grouped by run phase; each group is one hue in the colors
    values = [
        # bunkering LP, expected fleet
        profile.get_expected_build_time(),
        profile.get_expected_solve_time(),
        profile.get_expected_transfer_time(),
        # bunkering LP, existing fleet
        profile.get_existing_build_time(),
        profile.get_existing_solve_time(),
        profile.get_existing_transfer_time(),
        # fleet decisions
        profile.get_speed_time(),
        profile.get_retrofit_time(),
        profile.get_fleet_evolution_time(),
        profile.get_producer_evolution_time(),
        # setup and bookkeeping
        profile.get_temporal_time(),
        profile.get_fleet_state_time(),
        profile.get_overhead_time(),
        # domain calculations
        profile.get_vessel_time(),
        profile.get_fuel_supply_time(),
        profile.get_policy_time(),
        profile.get_profile_agg_time(),
    ]

    labels = [
        "Expected (build)",
        "Expected (solve)",
        "Expected (transfer)",
        "Existing (build)",
        "Existing (solve)",
        "Existing (transfer)",
        "Speed",
        "Retrofit",
        "Fleet evolution",
        "Producer evolution",
        "Temporal / expectations",
        "Fleet state",
        "Overhead",
        "Vessel operations",
        "Fuel supply chain",
        "Policy / regulation",
        "Profile aggregation",
    ]

    colors = [
        CENTER_COLORS_BLUE[2],
        CENTER_COLORS_BLUE[4],
        CENTER_COLORS_BLUE[6],
        CENTER_COLORS_GREEN[2],
        CENTER_COLORS_GREEN[4],
        CENTER_COLORS_GREEN[6],
        CENTER_COLORS_YELLOW[2],
        CENTER_COLORS_YELLOW[4],
        CENTER_COLORS_YELLOW[6],
        CENTER_COLORS_YELLOW[5],
        CENTER_COLORS_GREY[1],
        CENTER_COLORS_GREY[3],
        CENTER_COLORS_GREY[5],
        CENTER_COLORS_RED[1],
        CENTER_COLORS_RED[3],
        CENTER_COLORS_RED[5],
        CENTER_COLORS_RED[6],
    ]

    if cumulative:
        values = [to_cumulative(dateline, value) for value in values]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    total_cumulative = profile.get_total_time()
    if cumulative:
        ax.plot(dateline, total_cumulative, label="Total", color="k", ls="--", lw=2.0)
        ax.set_ylabel("Cumulative computational time [s]")
        suffix = "_cumulative"
    else:
        total_per_step = np.diff(total_cumulative, prepend=0.0)
        ax.plot(
            dateline,
            total_per_step,
            label="Total (per step)",
            color="k",
            ls="--",
            lw=2.0,
        )
        ax.set_ylabel("Computational time per step [s]")
        suffix = ""

    legend = ax.legend(stack[::-1], labels[::-1], ncol=2, **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, f"computational_performance{suffix}.png")


def plot_computational_performance(results: SimulationResults, directory: str) -> None:
    """Plot the computational time per time step by run phase."""
    _plot_computational_performance(results, directory, cumulative=False)


def plot_computational_performance_cumulative(
    results: SimulationResults, directory: str
) -> None:
    """Plot the cumulative computational time by run phase."""
    _plot_computational_performance(results, directory, cumulative=True)
