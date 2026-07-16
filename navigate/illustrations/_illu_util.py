# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import math


def subplot_layout(n):
    r = round(math.sqrt(n))
    c = math.ceil(n / r)
    return r, c


def set_font_sizes(ax, font_size=12, legend_size=10):

    # title and axis labels
    items = [ax.title, ax.xaxis.label, ax.yaxis.label]

    # offset text (e.g. scientific notation)
    items += [ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()]

    # add z-axis texts if 3D
    if ax.name == '3d':
        items += [ax.zaxis.label, ax.zaxis.get_offset_text()]

    # tick labels
    items += ax.get_xticklabels() + ax.get_yticklabels()

    # change all non-legend texts
    for item in items:
        item.set_fontsize(font_size)

    # legend
    legend = ax.get_legend()
    if legend is not None:
        for item in legend.get_texts():
            item.set_fontsize(legend_size)


def trim_axes(axes, n):
    """
    Reduce *axs* to *N* Axes. All further Axes are removed from the figure.
    """

    for ax in axes[n:]:
        ax.remove()

    return axes[:n]


def get_font_sizes(n):
    """

    Parameters
    ----------
    n : int
        Number of axes on the figure.

    Returns
    -------

    """

    labels = 25.
    legend = 25.

    if 1 <= n <= 6:

        labels -= 1. * (n - 1)
        legend -= 1. * (n - 1)

    elif n > 6:

        labels -= 0.8333 * (n - 6) + 1. * (6 - 1)
        legend -= 0.8333 * (n - 6) + 1. * (6 - 1)

    # anything below 7 is eligible
    labels = max(labels, 7.)
    legend = max(legend, 7.)

    return labels, legend
