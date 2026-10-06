# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the global installed engine power by fuel type."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._aggregate import (
    remove_below_threshold,
    unpack_fuel_type_series,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._labels import FUEL_TYPE_ORDER
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import find_best_metric_prefix

if TYPE_CHECKING:
    from navigate.core.simulation_results import SimulationResults


def plot_global_installed_power(results: SimulationResults, directory: str) -> None:
    """Plot the global installed engine power by fuel type."""
    dateline = results.dateline

    fig, ax = single_panel()

    installed_power = results.profile.get_installed_power()
    engine_power = {
        fuel_type: installed_power[fuel_type] for fuel_type in FUEL_TYPE_ORDER
    }

    remove_below_threshold(engine_power, 1.0)

    divisor, prefix = find_best_metric_prefix(
        np.amax(sum(list(engine_power.values()))), unit_order=6
    )
    engine_power = {
        fuel_type: power / divisor for fuel_type, power in engine_power.items()
    }
    unit = f"{prefix}W"

    values, labels, colors = unpack_fuel_type_series(engine_power)

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel(f"Installed power [{unit}]")
    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, "global_installed_power.png")
