# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.output.plots._aggregate import merge_fleet_evolution
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes


def plot_fleet_evolution(manager, directory):
    dateline = manager.get_dateline()
    fleets = manager.nodes.fleets

    fig, axes = subplot_grid(len(fleets), sharex=True)

    for ax, fleet in zip(axes, fleets.values()):

        values, labels, colors, title = merge_fleet_evolution(dateline, fleet)

        plot_stack_with_lines(ax, dateline, values, labels, colors)

        ax.set_ylabel('Number of vessels')
        ax.set_title(title)
        legend = None  # ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
        format_axes(ax, len(fleets), dateline, legend)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_evolution.png')
