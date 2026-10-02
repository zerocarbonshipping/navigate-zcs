# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Subplot grid shape, axes trimming and font sizing for the plot figures."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.text import Text


def subplot_layout(n: int) -> tuple[int, int]:
    rows = round(math.sqrt(n))
    columns = math.ceil(n / rows)
    return rows, columns


def set_font_sizes(ax: Axes, font_size: float, legend_size: float) -> None:
    items: list[Text] = [ax.title, ax.xaxis.label, ax.yaxis.label]

    items += [ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()]

    items += ax.get_xticklabels() + ax.get_yticklabels()

    for item in items:
        item.set_fontsize(font_size)

    legend = ax.get_legend()
    if legend is not None:
        for item in legend.get_texts():
            item.set_fontsize(legend_size)


def trim_axes(axes: list[Axes], n: int) -> None:
    """Remove the axes beyond the first *n* from their figure."""
    for ax in axes[n:]:
        ax.remove()


def get_font_sizes(n: int) -> tuple[float, float]:
    """
    Return (label, legend) font sizes scaled down with the number of axes.

    Parameters
    ----------
    n
        Number of axes on the figure.

    Returns
    -------
    tuple[float, float]
        Label and legend font sizes, points; never below 7.
    """
    labels = 25.0
    legend = 25.0

    if 1 <= n <= 6:
        labels -= 1.0 * (n - 1)
        legend -= 1.0 * (n - 1)

    elif n > 6:
        labels -= 0.8333 * (n - 6) + 1.0 * (6 - 1)
        legend -= 0.8333 * (n - 6) + 1.0 * (6 - 1)

    labels = max(labels, 7.0)
    legend = max(legend, 7.0)

    return labels, legend
