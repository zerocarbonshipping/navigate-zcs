# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)
from navigate.output.plots._labels import (
    FEEDSTOCK_COLOR,
    FEEDSTOCK_LABEL,
    extract_label,
)
from navigate.output.plots._units import get_best_unit_mass
from navigate.util import divide_nonzero


def plot_producer_feed_consumption(manager, directory):
    dateline = manager.get_dateline()

    producers = manager.nodes.producers
    feedstocks = manager.nodes.feedstocks
    processes = manager.nodes.processes
    feeds = {**feedstocks, **processes}

    colors = generate_color_dict(feeds, FEEDSTOCK_COLOR)

    if not producers:
        return

    for producer_name, producer in producers.items():

        results = {}
        profile = producer.profile

        for feed_name in feeds:

            consumed = profile.get_feed_mass(feed_name)
            constraint = profile.get_feed_constraint(feed_name)
            constraint = np.where(constraint == np.inf, np.nan, constraint)

            if np.all(np.isnan(constraint)):
                continue

            results[feed_name] = (consumed, constraint)

        if not results:
            continue

        fig, axes = subplot_grid(len(results))

        for ax, (feed_name, (consumed, constraint)) in zip(axes, results.items()):

            max_constraint = np.nanmax(constraint)

            maximum = max(np.nanmax(consumed), max_constraint)
            divisor, unit = get_best_unit_mass(maximum)

            plot_stack_with_lines(ax, dateline,
                                  [divide_nonzero(consumed, divisor)],
                                  ['Consumed'],
                                  [colors[feed_name]],
                                  alpha=0.7)

            ax.plot(dateline, divide_nonzero(constraint, divisor), 'k', label='Constraint')

            ax.set_ylabel('Feed [{}]'.format(unit))
            ax.set_title('{}'.format(extract_label(feeds[feed_name], FEEDSTOCK_LABEL)))
            legend = ax.legend()
            format_axes(ax, len(results), dateline, legend)

        trim_axes(axes, len(results))

        save_figure(fig, directory, 'producer_feed_consumption_{}.png'.format(producer_name))
