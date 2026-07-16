# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._colors import generate_color_dict
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import (
    FEEDSTOCK_COLOR,
    FEEDSTOCK_LABEL,
    extract_label,
)
from navigate.illustrations.plots._units import get_best_unit_mass
from navigate.util import divide_nonzero


def plot_global_feedstock_consumption(manager, directory):
    dateline = manager.get_dateline()

    feedstocks = manager.nodes.feedstocks
    profile = manager.profile

    if not feedstocks:
        return

    fig, axes = subplot_grid(len(feedstocks))
    colors = generate_color_dict(feedstocks, FEEDSTOCK_COLOR)

    for ax, feedstock_name in zip(axes, feedstocks):

        consumed = profile.get_feed_mass(feedstock_name)
        constraint = profile.get_feed_constraint(feedstock_name)
        constraint = np.where(constraint == np.inf, np.nan, constraint)

        if np.all(np.isnan(constraint)):
            max_constraint = 0.
        else:
            max_constraint = np.nanmax(constraint)

        maximum = max(np.nanmax(consumed), max_constraint)
        divisor, unit = get_best_unit_mass(maximum)

        plot_stack_with_lines(ax, dateline,
                              [divide_nonzero(consumed, divisor)],
                              ['Consumed'],
                              [colors[feedstock_name]],
                              alpha=0.7)

        if np.any(np.isfinite(constraint)):
            ax.plot(dateline, divide_nonzero(constraint, divisor), 'k', label='Constraint')

        ax.set_ylabel('Feedstock [{}]'.format(unit))
        ax.set_title('{}'.format(extract_label(feedstocks[feedstock_name], FEEDSTOCK_LABEL)))
        legend = ax.legend()
        format_axes(ax, len(feedstocks), dateline, legend)

    trim_axes(axes, len(feedstocks))

    save_figure(fig, directory, 'global_feedstock_consumption.png')
