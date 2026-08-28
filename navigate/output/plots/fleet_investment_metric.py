# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import FUEL_TYPE_COLOR
from navigate.output.plots._style import LEGEND_OPTIONS


def plot_fleet_investment_metric(manager, directory):
    dateline = manager.dateline
    fleets = manager.nodes.fleets

    unit = 'USD/k cargo-mile'
    divisor = 1. / 1e3

    for fleet in fleets.values():

        vessels = fleet.vessels

        fig, axes = subplot_grid(len(vessels), sharey=True)

        for ax, vessel in zip(axes, vessels):

            active = vessel.profile.is_active()
            expected = np.where(active, vessel.profile.get_investment_freight_rate(), np.nan)
            instantaneous = np.where(active, vessel.profile.get_instantaneous_freight_rate(), np.nan)

            color = FUEL_TYPE_COLOR[vessel.fuel_type]

            ax.plot(dateline[1:], expected[1:] / divisor,
                    color=color, label='Investment', lw=2.5, ls=(0, (5, 3)), alpha=0.5)

            if np.any(~np.isnan(instantaneous)):
                ax.plot(dateline[1:], instantaneous[1:] / divisor,
                        color=color, label='Instantaneous', lw=2.5)

            ax.set_ylabel('Freight rate [{}]'.format(unit))
            ax.set_title(vessel.name + ' vessel')
            legend = ax.legend(**LEGEND_OPTIONS)
            format_axes(ax, len(vessels), dateline, legend, y_lim=None)

        for ax in axes:
            ax.set_ylim([0., None])

        trim_axes(axes, len(vessels))

        save_figure(fig, directory, 'fleet_investment_metric_{}.png'.format(fleet.name))
