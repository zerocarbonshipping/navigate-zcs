# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the weighted average vessel age per fuel type."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
)
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def plot_engine_age(results: SimulationResults, directory: Path) -> None:
    """Plot the weighted average vessel age per fuel type."""
    dateline = results.dateline

    weighted_average_age = results.profile.get_weighted_average_age()

    # a fuel type without vessels has an age of zero throughout
    weighted_average_age = {
        fuel_type: age
        for fuel_type, age in weighted_average_age.items()
        if np.any(age > 0.0)
    }

    if not weighted_average_age:
        return

    fig, axes = subplot_grid(len(weighted_average_age))

    y_max = max(np.nanmax(age) for age in weighted_average_age.values())

    for ax, fuel_type in zip(axes, weighted_average_age, strict=False):
        age = weighted_average_age[fuel_type]
        ax.plot(dateline, age, color=FUEL_TYPE_COLOR[fuel_type], lw=2.0)
        ax.set_ylabel("Average age [years]")
        ax.set_title(f"{FUEL_TYPE_LABEL[fuel_type]} vessels")
        format_axes(ax, len(weighted_average_age), dateline)
        ax.set_ylim(0.0, y_max * 1.05)

    trim_axes(axes, len(weighted_average_age))

    save_figure(fig, directory, "engine_age.png")
