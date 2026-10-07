# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Matplotlib figure and axes plumbing shared by the plot modules.

Grid creation, stacked-area drawing, axis formatting, and figure saving.
Font sizes and subplot layout come from
:mod:`navigate.output.plots._layout`; save options from
:mod:`navigate.output.plots._style`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from navigate.output.plots._layout import (
    get_font_sizes,
    set_font_sizes,
    subplot_layout,
)
from navigate.output.plots._style import SAVE_OPTIONS

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from matplotlib.axes import Axes
    from matplotlib.collections import PolyCollection
    from matplotlib.figure import Figure
    from matplotlib.legend import Legend
    from matplotlib.typing import ColorType

    from navigate.util.types_ import DateArray, FloatArray

_FIGURE_SIZE = (27, 15)


def single_panel() -> tuple[Figure, Axes]:
    """Create a single-panel figure; return (fig, ax)."""
    return plt.subplots(1, 1, figsize=_FIGURE_SIZE)


def subplot_grid(
    count: int, *, sharex: bool = False, sharey: bool = False
) -> tuple[Figure, list[Axes]]:
    """Create a subplot grid sized for *count* panels; return (fig, flat axes list)."""
    fig, axes = plt.subplots(
        *subplot_layout(count),
        figsize=_FIGURE_SIZE,
        sharex=sharex,
        sharey=sharey,
        squeeze=False,
    )
    return fig, list(axes.flat)


def plot_stack_with_lines(
    ax: Axes,
    x: DateArray,
    values: Sequence[FloatArray],
    labels: Sequence[str],
    colors: Sequence[ColorType],
    alpha: float = 0.8,
) -> list[PolyCollection]:
    if not values:
        return []

    stack = ax.stackplot(x, *values, labels=labels, colors=colors, alpha=alpha)

    # draw the outlines top-down so each lower outline stays visible
    cumulative = [np.add.reduce(values[: (i + 1)]) for i in range(len(values))]

    for value, color in zip(cumulative[::-1], colors[::-1], strict=True):
        ax.plot(x, value, color=color, lw=2)

    return stack


def format_axes(
    ax: Axes,
    count: int,
    dateline: DateArray,
    legend: Legend | None = None,
    y_lim: tuple[float | None, float | None] | None = (0.0, None),
) -> None:
    """
    Apply the shared limits, grid and font sizes to one panel.

    Parameters
    ----------
    ax
        Panel to format.
    count
        Number of panels on the figure, which scales the font sizes.
    dateline
        Dates whose first and last entries bound the x-axis.
    legend
        The panel's legend; its patches shrink on figures of more than 12 panels.
    y_lim
        Lower and upper y-axis limits, each None to keep the current one; None
        leaves the y-axis untouched.
    """
    if y_lim is not None:
        ax.set_ylim(*y_lim)

    ax.set_xlim(dateline[0], dateline[-1])

    ax.grid(True, lw=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    set_font_sizes(ax, *get_font_sizes(count))

    if legend is not None and count > 12:
        for patch in legend.get_patches():
            if isinstance(patch, Rectangle):
                patch.set_width(patch.get_width() * 0.8)
                patch.set_height(patch.get_height() * 0.8)


def save_figure(fig: Figure, directory: Path, filename: str) -> None:
    """Save *fig* to ``directory/filename`` with the standard options and close it."""
    fig.savefig(directory / filename, bbox_inches="tight", **SAVE_OPTIONS)
    plt.close(fig)
