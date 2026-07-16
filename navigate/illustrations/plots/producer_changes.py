# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import matplotlib.patches as mpatches

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._aggregate import merge_producer_changes
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._style import (
    LEGEND_OPTIONS,
)


def plot_producer_changes(manager, directory):

    dateline = manager.get_dateline()
    producers = manager.nodes.producers

    if not producers:
        return

    fig, axes = subplot_grid(len(producers))

    for ax, producer in zip(axes, producers.values()):

        scraps, scrap_labels, scrap_colors, title = merge_producer_changes(dateline, producer, decommission=True)
        builds, build_labels, build_colors, _ = merge_producer_changes(dateline, producer, decommission=False)

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

        patches = [mpatches.Patch(color=color, label=label) for label, color in zip(unique_labels, unique_colors)]

        ax.set_ylabel('# plants/year')
        ax.set_title(title)
        legend = ax.legend(handles=patches, **LEGEND_OPTIONS)
        format_axes(ax, len(producers), dateline, legend=legend, y_lim=(None, None))

    trim_axes(axes, len(producers))

    save_figure(fig, directory, 'producer_changes.png')
