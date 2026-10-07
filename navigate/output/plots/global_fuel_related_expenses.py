# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the global fuel, levy and regulation expenses."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._aggregate import to_cumulative
from navigate.output.plots._colors import (
    CENTER_COLORS_GREEN,
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
from navigate.output.plots._units import get_best_unit_cost

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def _plot_global_fuel_related_expenses(
    results: SimulationResults, directory: Path, cumulative: bool
) -> None:
    dateline = results.dateline

    fig, ax = single_panel()

    profile = results.profile
    fuel_expenses = profile.get_total_fuel_expenses()
    levy_expenses = profile.get_total_levy_expenses()
    regulation_expenses = profile.get_regulation_expenses()

    values = [fuel_expenses, levy_expenses, regulation_expenses]

    if cumulative:
        values = [to_cumulative(dateline, value) for value in values]

    divisor, unit = get_best_unit_cost(np.amax(sum(values)), rate=not cumulative)

    values = [value / divisor for value in values]
    labels = ["Fuel", "Levy", "Regulation"]
    colors = [CENTER_COLORS_GREEN[3], CENTER_COLORS_YELLOW[3], CENTER_COLORS_RED[3]]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    if cumulative:
        ax.set_ylabel(f"Cumulative expenses [{unit}]")
        suffix = "_cumulative"
    else:
        ax.set_ylabel(f"Expenses [{unit}]")
        suffix = ""

    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, f"global_fuel_related_expenses{suffix}.png")


def plot_global_fuel_related_expenses(
    results: SimulationResults, directory: Path
) -> None:
    """Plot the yearly global fuel, levy and regulation expenses."""
    _plot_global_fuel_related_expenses(results, directory, cumulative=False)


def plot_global_fuel_related_expenses_cumulative(
    results: SimulationResults, directory: Path
) -> None:
    """Plot the cumulative global fuel, levy and regulation expenses."""
    _plot_global_fuel_related_expenses(results, directory, cumulative=True)
