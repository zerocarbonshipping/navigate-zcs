# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import FUEL_COLOR


def plot_plant_production_emissions(manager, directory):

    dateline = manager.get_dateline()
    fuels = manager.nodes.fuels
    regions = manager.nodes.regions
    plants = manager.nodes.plants
    emissions = manager.nodes.emissions
    emissions_lifetime = manager.general_nodes.model_definition.get_emissions_lifetime()

    colors = generate_color_dict(fuels, FUEL_COLOR)

    for region_name, region in regions.items():

        plants_region = [plant for plant in plants.values() if plant.region is region]
        plants_region = sorted(plants_region, key=lambda x: x.get_name())
        n = len(plants_region)

        if not plants_region:
            continue

        fig, axes = subplot_grid(n)

        # track min/max
        y_min = 0.
        y_max = 0.

        for ax, plant in zip(axes, plants_region):

            fuel = plant.fuel
            fuel_name = fuel.get_name()
            lhv = fuel.lower_heating_value.get()

            TTW = 0.
            for emission_name, emission in emissions.items():
                TTW += fuel.get_TTW(emission_name).get() * emission.global_warming_potential.get(emissions_lifetime)

            profile = plant.profile
            investment = np.round((profile.get_total_equivalent_investment_WTT() + TTW) / lhv * 1e3, 5)
            instantaneous = np.round((profile.get_total_equivalent_instantaneous_WTT() + TTW) / lhv * 1e3, 5)

            # update axes limits
            investment_lim = np.where(np.isnan(investment), 0., investment)
            instantaneous_lim = np.where(np.isnan(instantaneous), 0., instantaneous)
            y_min = min(y_min, np.amin(investment_lim), np.amin(instantaneous_lim))
            y_max = max(y_max, np.amax(investment_lim), np.amax(instantaneous_lim))

            ax.plot(dateline, investment, color=colors[fuel_name], label='Investment', lw=2.5, ls='--')
            ax.plot(dateline, instantaneous, color=colors[fuel_name], label='Instantaneous', lw=2.5)

            ax.set_title(plant.get_name())
            ax.set_ylabel('WTW [kgCO$_2$-eq/GJ]')
            legend = ax.legend()
            format_axes(ax, n, dateline, legend, y_lim=(None, None))

        for ax in axes:
            ax.set_ylim((y_min * 1.05, y_max * 1.05))

        trim_axes(axes, n)

        save_figure(fig, directory, 'plant_production_emissions_{}.png'.format(region_name))
