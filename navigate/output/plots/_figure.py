# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Matplotlib figure and axes plumbing shared by the plot modules.

Grid creation, stacked-area drawing, axis formatting, and figure saving.
Font sizes and subplot layout come from
:mod:`navigate.output.plots._illu_util`; save options from
:mod:`navigate.output.plots._style`.
"""

import os

import matplotlib.pyplot as plt
import numpy as np

from navigate.output.plots._illu_util import (
    get_font_sizes,
    set_font_sizes,
    subplot_layout,
)
from navigate.output.plots._style import SAVE_OPTIONS


def ensure_axes_list(axes):
    """Ensure axes is always a flat list, even for a single subplot."""
    try:
        return axes.flatten()
    except AttributeError:
        return [axes]


def single_panel(figsize=(27, 15), **kwargs):
    """Create a single-panel figure; return (fig, ax)."""
    return plt.subplots(1, 1, figsize=figsize, **kwargs)


def subplot_grid(n, figsize=(27, 15), **kwargs):
    """Create a subplot grid sized for *n* panels; return (fig, flat axes list)."""
    fig, axes = plt.subplots(*subplot_layout(n), figsize=figsize, **kwargs)
    return fig, ensure_axes_list(axes)


def plot_stack_with_lines(ax, x, values, labels, colors, alpha=0.8):

    if not values:
        return []

    stack = ax.stackplot(x, *values, labels=labels, colors=colors, alpha=alpha)

    # plot lines between the stacks (in reverse order)
    cumulative = [np.add.reduce(values[:(i + 1)]) for i in range(len(values))]

    for value, color in zip(cumulative[::-1], colors[::-1]):
        ax.plot(x, value, color=color, lw=2)

    return stack


def format_axes(ax, n, dateline=None, legend=None, y_lim=(0., None)):

    # set limits
    if y_lim is not None:
        ax.set_ylim(y_lim)

    if dateline is not None:
        ax.set_xlim((dateline[0], dateline[-1]))

    # apply grid lines
    ax.grid(True, lw=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # format font sizes
    set_font_sizes(ax, *get_font_sizes(n))

    # format legend size
    if legend is not None:

        if n > 12:
            for patch in legend.get_patches():
                patch.set_width(patch.get_width() * 0.8)
                patch.set_height(patch.get_height() * 0.8)


def save_figure(fig, directory, filename):
    """Save *fig* to ``directory/filename`` with the standard options and close it."""
    path = os.path.join(directory, filename)
    fig.savefig(path, bbox_inches='tight', **SAVE_OPTIONS)
    plt.close(fig)
