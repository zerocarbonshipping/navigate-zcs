# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the share of the global installed engine power per fuel type."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._aggregate import (
    remove_below_threshold,
    unpack_fuel_type_series,
)
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FUEL_TYPE_ORDER
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData


def plot_global_installed_power_share(plot_data: PlotData, directory: str) -> None:
    """Plot the share of the global installed engine power per fuel type."""
    dateline = plot_data.dateline

    installed_power = plot_data.profile.get_installed_power()
    engine_power = {
        fuel_type: installed_power[fuel_type] for fuel_type in FUEL_TYPE_ORDER
    }

    remove_below_threshold(engine_power, 1.0)
    total_power = sum(list(engine_power.values()))
    engine_power = {
        fuel_type: power / total_power * 100.0
        for fuel_type, power in engine_power.items()
    }

    values, labels, colors = unpack_fuel_type_series(engine_power)

    fig, axes = subplot_grid(len(values), sharey=True)

    for ax, value, label, color in zip(axes, values, labels, colors, strict=False):
        ax.plot(dateline, value, color=color, lw=2.5)

        ax.set_title(label)
        ax.set_ylabel("Market share [%]")
        format_axes(ax, len(values), dateline)

    for ax in axes:
        ax.set_ylim(0.0, 100.0)

    trim_axes(axes, len(values))

    save_figure(fig, directory, "global_installed_power_share.png")
