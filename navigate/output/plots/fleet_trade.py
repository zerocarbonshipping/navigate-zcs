# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import matplotlib.lines as mlines
import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import FLEET_LABEL, extract_label
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_cargo_miles


def plot_fleet_trade(manager, directory):
    dateline = manager.dateline
    fleets = manager.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    fleet_label = 'Modelled'
    assumed_label = 'Target'
    fleet_color = np.array([60., 94., 134.]) / 255.
    assumed_color = np.array([194., 128., 128.]) / 255.

    fleet_trades = [fleet.profile.get_trade() for fleet in fleets.values()]
    assumed_trades = [fleet.trade for fleet in fleets.values()]

    divisor, unit = get_best_unit_cargo_miles(
        max(max(np.amax(trade) for trade in fleet_trades),
            max(np.amax(trade) for trade in assumed_trades)))

    fleet_trades = [trade / divisor for trade in fleet_trades]
    assumed_trades = [trade / divisor for trade in assumed_trades]

    for ax, fleet, fleet_trade, assumed_trade in zip(axes, fleets.values(), fleet_trades, assumed_trades):

        # plot stacks
        stack = ax.stackplot(dateline, fleet_trade, labels=[fleet_label], colors=[fleet_color], alpha=0.8)
        ax.plot(dateline, fleet_trade, color=fleet_color, lw=2)
        ax.plot(dateline, assumed_trade, label=assumed_label, color=assumed_color, ls='--', lw=3)

        proxy_line = mlines.Line2D([], [], color=assumed_color, label=assumed_label, lw=3)

        ax.set_ylabel('Trade [{}]'.format(unit))
        ax.set_title(extract_label(fleet, FLEET_LABEL))

        legend = ax.legend([*stack, proxy_line], [fleet_label, assumed_label], **LEGEND_OPTIONS)
        format_axes(ax, len(fleets), dateline, legend)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_trade.png')
