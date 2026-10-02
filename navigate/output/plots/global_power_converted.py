# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the engine power converted between fuel types."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import numpy as np

from navigate.output.plots._aggregate import unpack_fuel_type_series
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import find_best_metric_prefix
from navigate.util import (
    TOLERANCE,
    dates_to_years,
    divide_nonzero,
    sum_by_first_key,
    sum_by_second_key,
)

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData


def plot_global_power_converted_cumulative(plot_data: PlotData, directory: str) -> None:
    """Plot the cumulative engine power converted from and to each fuel type."""
    dateline = plot_data.dateline

    fig, ax = single_panel()

    converted_power = plot_data.profile.get_fuel_converted_power()
    converted_power = {
        key: value
        for key, value in converted_power.items()
        if np.any(np.abs(value) > TOLERANCE)
    }

    divisor, prefix = find_best_metric_prefix(
        np.amax(np.sum(list(converted_power.values()))), unit_order=6
    )
    converted_power = {
        key: divide_nonzero(power, divisor) for key, power in converted_power.items()
    }
    unit = f"{prefix}W"

    conversions_from = {
        key: -conversion
        for key, conversion in sum_by_first_key(converted_power).items()
    }
    conversions_to = sum_by_second_key(converted_power)

    values_from, labels_from, colors_from = unpack_fuel_type_series(conversions_from)
    values_to, labels_to, colors_to = unpack_fuel_type_series(conversions_to)

    time_steps = np.diff(dates_to_years(dateline))
    values_from = [np.cumsum(value[1:] * time_steps) for value in values_from]
    values_to = [np.cumsum(value[1:] * time_steps) for value in values_to]

    plot_stack_with_lines(ax, dateline[1:], values_from, labels_from, colors_from)
    plot_stack_with_lines(ax, dateline[1:], values_to, labels_to, colors_to)

    # one legend entry per fuel type, whether converted from or to
    unique_labels = [*labels_from]
    unique_colors = [*colors_from]

    for label, color in zip(labels_to, colors_to, strict=True):
        if label not in unique_labels:
            unique_labels.append(label)
            unique_colors.append(color)

    ax.plot([dateline[1], dateline[-1]], [0.0, 0.0], c="k", lw=2)

    ax.set_ylabel(f"Converted power [{unit}]")

    patches = [
        mpatches.Patch(color=color, label=label)
        for label, color in zip(unique_labels, unique_colors, strict=True)
    ]
    legend = ax.legend(handles=patches, **LEGEND_OPTIONS)

    format_axes(ax, 1, dateline[1:], legend, y_lim=(None, None))

    save_figure(fig, directory, "global_power_converted_cumulative.png")
