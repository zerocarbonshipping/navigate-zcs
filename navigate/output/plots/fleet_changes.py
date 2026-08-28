# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.output.plots._aggregate import merge_fleet_changes
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes


def plot_fleet_changes(manager, directory):
    dateline = manager.dateline
    fleets = manager.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    for ax, fleet in zip(axes, fleets.values()):

        scraps, scrap_labels, scrap_colors, title = merge_fleet_changes(dateline, fleet, scrap=True)
        builds, build_labels, build_colors, _ = merge_fleet_changes(dateline, fleet, scrap=False)

        plot_stack_with_lines(ax, dateline, scraps, scrap_labels, scrap_colors)
        plot_stack_with_lines(ax, dateline, builds, build_labels, build_colors)

        # plot zero line
        ax.plot([dateline[0], dateline[-1]], [0., 0.], c='k', lw=2)

        # create proxy artist for legend
        unique_labels = [*scrap_labels]
        unique_colors = [*scrap_colors]

        for label, color in zip(build_labels, build_colors):

            if label not in unique_labels:

                unique_labels.append(label)
                unique_colors.append(color)

        ax.set_ylabel('# vessels/year')
        ax.set_title(title)
        format_axes(ax, len(fleets), dateline, legend=None, y_lim=(None, None))

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_changes.png')
