# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._aggregate import merge_fuel_costs
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)


def plot_port_bunker_price(manager, directory):
    dateline = manager.get_dateline()
    fuels = manager.nodes.fuels
    ports = manager.nodes.ports

    for port_name, port in ports.items():

        fuel_costs = {fuel.get_name():
                      port.profile.get_bunker_price(fuel.get_name())
                      / fuel.lower_heating_value.get() for fuel in fuels.values()}

        # remove unavailable time of fuel
        fuel_costs = {fuel_name: np.where(cost == 0., np.nan, cost) for fuel_name, cost in fuel_costs.items()}

        values, colors, titles = merge_fuel_costs(fuel_costs, fuels)

        if not titles:
            continue

        fig, axes = subplot_grid(len(titles), sharey=True)

        min_value = 0.

        for ax, value, color, title in zip(axes, values, colors, titles):

            for i in range(len(value)):
                ax.plot(dateline, value[i], color=color[i], lw=2.5)
                min_value = min(min_value, np.amin(value[i]))

            ax.set_ylabel('Bunker price [USD/GJ]')
            legend = None  # ax.legend(loc='upper right', **LEGEND_OPTIONS)

            ax.set_title(title, color='k')
            format_axes(ax, len(values), dateline, legend, y_lim=None)

        if min_value == 0.:
            for ax in axes:
                ax.set_ylim((0., None))

        trim_axes(axes, len(titles))

        save_figure(fig, directory, 'port_bunker_price_{}.png'.format(port_name))
