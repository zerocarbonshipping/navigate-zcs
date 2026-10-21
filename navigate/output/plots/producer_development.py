# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the plant development per producer, yearly and cumulative."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._aggregate import to_cumulative
from navigate.output.plots._colors import CENTER_COLORS_GREEN
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._style import LEGEND_OPTIONS

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.output.simulation_results import SimulationResults


def _plot_producer_development(
    results: SimulationResults, directory: Path, cumulative: bool
) -> None:
    dateline = results.dateline
    producers = results.nodes.producers

    if not producers:
        return

    fig, axes = subplot_grid(len(producers))

    for ax, producer in zip(axes, producers.values(), strict=False):
        producer_results = producer.results

        if cumulative:
            # development counts the plants added in each step, the constraint is
            # a rate per year
            development = np.cumsum(producer_results.development)
            development_constraint = to_cumulative(
                dateline, producer_results.maximum_development
            )
        else:
            development = producer_results.development
            development_constraint = producer_results.maximum_development

        ax.plot(
            dateline, development, label="Planned", color=CENTER_COLORS_GREEN[3], lw=2.0
        )
        ax.plot(dateline, development_constraint, "k--", label="Constraint", lw=2.0)

        legend = ax.legend(**LEGEND_OPTIONS)
        ax.set_title(producer.name)

        if cumulative:
            ax.set_ylabel("Development [plants]")
        else:
            ax.set_ylabel("Development [plants/year]")

        format_axes(ax, len(producers), dateline, legend)

    suffix = "_cumulative" if cumulative else ""

    save_figure(fig, directory, f"producer_development{suffix}.png")


def plot_producer_development(results: SimulationResults, directory: Path) -> None:
    """Plot the yearly plant development per producer against its constraint."""
    _plot_producer_development(results, directory, cumulative=False)


def plot_producer_development_cumulative(
    results: SimulationResults, directory: Path
) -> None:
    """Plot the cumulative plant development per producer against its constraint."""
    _plot_producer_development(results, directory, cumulative=True)
