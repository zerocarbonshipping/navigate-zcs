# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the feed consumption against the constraint, one figure per producer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FEEDSTOCK_COLOR,
    FEEDSTOCK_LABEL,
    extract_label,
)
from navigate.output.plots._layout import trim_axes
from navigate.output.plots._units import get_best_unit_mass
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData
    from navigate.util.types_ import FloatArray


def plot_producer_feed_consumption(plot_data: PlotData, directory: str) -> None:
    """Plot the feed consumption against the constraint, one figure per producer."""
    dateline = plot_data.dateline
    producers = plot_data.nodes.producers

    if not producers:
        return

    feeds = {**plot_data.nodes.feedstocks, **plot_data.nodes.processes}
    colors = generate_color_dict(feeds, FEEDSTOCK_COLOR)

    for producer_name, producer in producers.items():
        results: dict[str, tuple[FloatArray, FloatArray]] = {}
        profile = producer.profile
        feed_mass = profile.get_feed_mass()
        feed_constraint = profile.get_feed_constraint()

        for feed_name in feeds:
            consumed = feed_mass[feed_name]
            constraint = feed_constraint[feed_name]
            constraint = np.where(constraint == np.inf, np.nan, constraint)

            if np.all(np.isnan(constraint)):
                continue

            results[feed_name] = (consumed, constraint)

        if not results:
            continue

        fig, axes = subplot_grid(len(results))

        for ax, (feed_name, (consumed, constraint)) in zip(
            axes, results.items(), strict=False
        ):
            max_constraint = np.nanmax(constraint)

            maximum = max(np.nanmax(consumed), max_constraint)
            divisor, unit = get_best_unit_mass(maximum)

            plot_stack_with_lines(
                ax,
                dateline,
                [divide_nonzero(consumed, divisor)],
                ["Consumed"],
                [colors[feed_name]],
                alpha=0.7,
            )

            ax.plot(
                dateline, divide_nonzero(constraint, divisor), "k", label="Constraint"
            )

            ax.set_ylabel(f"Feed [{unit}]")
            ax.set_title(extract_label(feeds[feed_name], FEEDSTOCK_LABEL))
            legend = ax.legend()
            format_axes(ax, len(results), dateline, legend)

        trim_axes(axes, len(results))

        save_figure(fig, directory, f"producer_feed_consumption_{producer_name}.png")
