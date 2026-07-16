# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._aggregate import to_cumulative
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FUEL_TYPE_COLOR


def plot_fleet_orderbook(manager, directory):

    dateline = manager.get_dateline()
    timeline = manager.get_timeline()
    fleets = manager.nodes.fleets

    for fleet_name, fleet in fleets.items():

        orderbooks = fleet.orderbooks

        if not orderbooks:
            continue

        vessels = fleet.get_vessels()
        fig, axes = subplot_grid(len(vessels))

        profile = fleet.profile

        for v, (ax, vessel) in enumerate(zip(axes, vessels)):

            orderbook = orderbooks[v]

            values = orderbook.get(timeline)

            vessel_name = vessel.get_name()
            fuel_type = vessel.fuel_type

            ax.plot(dateline, values, color='k', label='Orderbook', lw=2.)

            modelled = to_cumulative(dateline, profile.get_orderbook_newbuilds(vessel_name))

            ax.plot(dateline, modelled, color=FUEL_TYPE_COLOR[fuel_type], ls='--', label='Model', lw=2.)

            ax.set_title(vessel_name)
            ax.set_ylabel('# of vessels')

            legend = ax.legend()
            format_axes(ax, len(vessels), dateline, legend=legend)

        trim_axes(axes, len(vessels))

        save_figure(fig, directory, 'fleet_orderbook_{}.png'.format(fleet_name))
