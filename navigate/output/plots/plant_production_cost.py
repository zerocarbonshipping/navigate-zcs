# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)
from navigate.output.plots._labels import FUEL_COLOR


def plot_plant_production_cost(manager, directory):

    dateline = manager.dateline
    fuels = manager.nodes.fuels
    regions = manager.nodes.regions
    plants = manager.nodes.plants

    colors = generate_color_dict(fuels, FUEL_COLOR)

    min_val = 0.

    for region_name, region in regions.items():

        plants_region = [plant for plant in plants.values() if plant.region is region]
        plants_region = sorted(plants_region, key=lambda x: x.name)
        n = len(plants_region)

        if not plants_region:
            continue

        fig, axes = subplot_grid(n, sharey=True)

        for ax, plant in zip(axes, plants_region):

            fuel = plant.fuel
            fuel_name = fuel.name
            lhv = fuel.lower_heating_value.get()

            profile = plant.profile
            investment = profile.get_investment_cost() / lhv
            instantaneous = profile.get_instantaneous_cost() / lhv

            min_val = min(min_val, np.amin(investment), np.amin(instantaneous))

            ax.plot(dateline, investment, color=colors[fuel_name], label='Investment', lw=2.5, ls='--')
            ax.plot(dateline, instantaneous, color=colors[fuel_name], label='Instantaneous', lw=2.5)

            ax.set_title(plant.name)
            ax.set_ylabel('Levelized cost [USD/GJ]')
            legend = ax.legend()
            format_axes(ax, n, dateline, legend, y_lim=None)

        if min_val >= 0.:
            for ax in axes:
                ax.set_ylim([0., None])

        trim_axes(axes, n)

        save_figure(fig, directory, 'plant_production_cost_{}.png'.format(region_name))
