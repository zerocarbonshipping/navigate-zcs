# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the fuels consumed by the engines of each fuel type."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._aggregate import (
    merge_fuels_for_plot,
    remove_below_threshold,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FUEL_TYPE_LABEL
from navigate.output.plots._layout import trim_axes
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_energy

if TYPE_CHECKING:
    from matplotlib.legend import Legend

    from navigate.output.plot_data import PlotData


def plot_engine_fuel_consumed(plot_data: PlotData, directory: str) -> None:
    """Plot the fuels consumed by the engines of each fuel type."""
    dateline = plot_data.dateline

    fuels = plot_data.nodes.fuels
    engine_fuel_consumed = plot_data.profile.get_converter_energy()

    for consumed in engine_fuel_consumed.values():
        remove_below_threshold(consumed, 1.0)

    engine_fuel_consumed = {
        fuel_type: consumed
        for fuel_type, consumed in engine_fuel_consumed.items()
        if consumed
    }

    maximum = max(
        np.amax(sum(list(consumed.values())))
        for consumed in engine_fuel_consumed.values()
    )
    divisor, unit = get_best_unit_energy(maximum, unit_order=9)

    fig, axes = subplot_grid(len(engine_fuel_consumed))

    for ax, fuel_type in zip(axes, engine_fuel_consumed, strict=False):
        fuel_consumed = {
            fuel_name: consumed / divisor
            for fuel_name, consumed in engine_fuel_consumed[fuel_type].items()
        }

        values, labels, colors = merge_fuels_for_plot(dateline, fuels, fuel_consumed)

        legend: Legend | None = None
        if values:
            stack = plot_stack_with_lines(ax, dateline, values, labels, colors)
            legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)

        ax.set_ylabel(f"Fuel consumed [{unit}]")
        ax.set_title(f"{FUEL_TYPE_LABEL[fuel_type]} vessels")
        format_axes(ax, len(engine_fuel_consumed), dateline, legend)

    trim_axes(axes, len(engine_fuel_consumed))

    save_figure(fig, directory, "engine_fuel_consumed.png")
