# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._colors import center_color_saturation
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FUEL_LABEL, extract_label


def plot_producer_fair_share(manager, directory):
    dateline = manager.get_dateline()

    fuels = manager.nodes.fuels
    fuels = {fuel_name: fuel for fuel_name, fuel in fuels.items() if not fuel.belongs_to_liquid_market()}
    producers = manager.nodes.producers

    if not producers:
        return

    colors = center_color_saturation(len(producers))

    fig, axes = subplot_grid(len(fuels))

    for ax, (fuel_name, fuel) in zip(axes, fuels.items()):

        added_lines = False
        for i, (producer_name, producer) in enumerate(producers.items()):

            if not producer.can_produce(fuel_name):
                continue

            fair_share = producer.profile.get_fair_share_fuel_fraction(fuel_name)

            label = producer_name
            ax.plot(dateline[1:], fair_share[1:], color=colors[i], label=label, lw=2.)
            added_lines = True

        ax.set_ylim([0., 1.03])

        ax.set_ylabel('Fair-share [-]')
        ax.set_title(extract_label(fuel, FUEL_LABEL))

        legend = None
        if added_lines:
            legend = ax.legend()

        format_axes(ax, len(fuels), dateline, legend)

    trim_axes(axes, len(fuels))

    save_figure(fig, directory, 'producer_fair_share.png')
