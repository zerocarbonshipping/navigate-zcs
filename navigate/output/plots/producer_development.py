# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._colors import CENTER_COLORS_GREEN
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._style import LEGEND_OPTIONS


def _plot_producer_development(manager, directory, cumulative=False):

    dateline = manager.dateline
    producers = manager.nodes.producers

    if not producers:
        return

    fig, axes = subplot_grid(len(producers))

    # cumulate fuel spent over all fleets
    for ax, producer in zip(axes, producers.values()):

        profile = producer.profile

        if cumulative:
            development = profile.get_cumulative_development()
            development_constraint = profile.get_cumulative_maximum_development()
        else:
            development = profile.get_development()
            development_constraint = profile.get_maximum_development()

        ax.plot(dateline, development, label='Planned', color=CENTER_COLORS_GREEN[3], lw=2.)

        if np.any(np.isfinite(development_constraint)):
            ax.plot(dateline, development_constraint, 'k--', label='Constraint', lw=2.)

        legend = ax.legend(**LEGEND_OPTIONS)
        ax.set_title(producer.name)

        if cumulative:
            ax.set_ylabel('Development [plants]')
        else:
            ax.set_ylabel('Development [plants/year]')

        format_axes(ax, len(producers), dateline, legend=legend)

    save_figure(fig, directory, 'producer_development{}.png'.format('_cumulative' if cumulative else ''))


def plot_producer_development(manager, directory):
    _plot_producer_development(manager, directory, cumulative=False)


def plot_producer_development_cumulative(manager, directory):
    _plot_producer_development(manager, directory, cumulative=True)
