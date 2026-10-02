# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the fair share of each producer per fuel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._colors import center_color_saturation
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FUEL_LABEL, extract_label
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from matplotlib.legend import Legend

    from navigate.output.plot_data import PlotData


def plot_producer_fair_share(plot_data: PlotData, directory: str) -> None:
    """Plot the fair share of each producer per fuel."""
    dateline = plot_data.dateline
    fuels = {
        fuel_name: fuel
        for fuel_name, fuel in plot_data.nodes.fuels.items()
        if not fuel.liquid_market
    }
    producers = plot_data.nodes.producers

    if not producers:
        return

    colors = center_color_saturation(len(producers))
    fair_shares = {
        producer_name: producer.profile.get_fair_share_fuel_fraction()
        for producer_name, producer in producers.items()
    }

    fig, axes = subplot_grid(len(fuels))

    for ax, (fuel_name, fuel) in zip(axes, fuels.items(), strict=False):
        added_lines = False
        for i, (producer_name, producer) in enumerate(producers.items()):
            if not producer.can_produce(fuel_name):
                continue

            fair_share = fair_shares[producer_name][fuel_name]
            ax.plot(
                dateline[1:],
                fair_share[1:],
                color=colors[i],
                label=producer_name,
                lw=2.0,
            )
            added_lines = True

        ax.set_ylim(0.0, 1.03)

        ax.set_ylabel("Fair-share [-]")
        ax.set_title(extract_label(fuel, FUEL_LABEL))

        legend: Legend | None = None
        if added_lines:
            legend = ax.legend()

        format_axes(ax, len(fuels), dateline, legend)

    trim_axes(axes, len(fuels))

    save_figure(fig, directory, "producer_fair_share.png")
