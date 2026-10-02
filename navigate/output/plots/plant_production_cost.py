# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the levelized production cost per plant, one figure per region."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import FUEL_COLOR
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData


def plot_plant_production_cost(plot_data: PlotData, directory: str) -> None:
    """Plot the levelized production cost per plant, one figure per region."""
    dateline = plot_data.dateline
    fuels = plot_data.nodes.fuels
    regions = plot_data.nodes.regions
    plants = plot_data.nodes.plants

    colors = generate_color_dict(fuels, FUEL_COLOR)

    min_cost = 0.0

    for region_name, region in regions.items():
        plants_region = sorted(
            (plant for plant in plants.values() if plant.region is region),
            key=lambda plant: plant.name,
        )

        if not plants_region:
            continue

        plant_count = len(plants_region)

        fig, axes = subplot_grid(plant_count, sharey=True)

        for ax, plant in zip(axes, plants_region, strict=False):
            fuel = plant.fuel
            fuel_name = fuel.name
            lhv = fuel.lower_heating_value.get()

            profile = plant.profile
            investment = profile.get_investment_cost() / lhv
            instantaneous = profile.get_instantaneous_cost() / lhv

            min_cost = min(min_cost, np.amin(investment), np.amin(instantaneous))

            ax.plot(
                dateline,
                investment,
                color=colors[fuel_name],
                label="Investment",
                lw=2.5,
                ls="--",
            )
            ax.plot(
                dateline,
                instantaneous,
                color=colors[fuel_name],
                label="Instantaneous",
                lw=2.5,
            )

            ax.set_title(plant.name)
            ax.set_ylabel("Levelized cost [USD/GJ]")
            legend = ax.legend()
            format_axes(ax, plant_count, dateline, legend, y_lim=None)

        if min_cost >= 0.0:
            for ax in axes:
                ax.set_ylim(0.0, None)

        trim_axes(axes, plant_count)

        save_figure(fig, directory, f"plant_production_cost_{region_name}.png")
