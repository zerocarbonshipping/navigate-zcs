# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the WTW emission intensity per plant, one figure per region."""

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
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def plot_plant_production_emissions(
    results: SimulationResults, directory: Path
) -> None:
    """Plot the WTW emission intensity per plant, one figure per region."""
    dateline = results.dateline
    fuels = results.nodes.fuels
    regions = results.nodes.regions
    plants = results.nodes.plants
    emissions = results.nodes.emissions
    emissions_lifetime = results.general_nodes.model_definition.emissions_lifetime

    colors = generate_color_dict(fuels, FUEL_COLOR)

    for region_name, region in regions.items():
        plants_region = sorted(
            (plant for plant in plants.values() if plant.region is region),
            key=lambda plant: plant.name,
        )

        if not plants_region:
            continue

        plant_count = len(plants_region)

        fig, axes = subplot_grid(plant_count)

        y_min = 0.0
        y_max = 0.0

        for ax, plant in zip(axes, plants_region, strict=False):
            fuel = plant.fuel
            fuel_name = fuel.name
            lhv = fuel.lower_heating_value.get()

            ttw = 0.0
            for emission_name, emission in emissions.items():
                ttw += fuel.ttw[
                    emission_name
                ].get() * emission.global_warming_potential.get(emissions_lifetime)

            profile = plant.profile
            investment = np.round(
                (profile.get_total_equivalent_investment_wtt() + ttw) / lhv * 1e3, 5
            )
            instantaneous = np.round(
                (profile.get_total_equivalent_instantaneous_wtt() + ttw) / lhv * 1e3, 5
            )

            investment_lim = np.where(np.isnan(investment), 0.0, investment)
            instantaneous_lim = np.where(np.isnan(instantaneous), 0.0, instantaneous)
            y_min = min(y_min, np.amin(investment_lim), np.amin(instantaneous_lim))
            y_max = max(y_max, np.amax(investment_lim), np.amax(instantaneous_lim))

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
            ax.set_ylabel("WTW [kgCO$_2$-eq/GJ]")
            legend = ax.legend()
            format_axes(ax, plant_count, dateline, legend, y_lim=(None, None))

        for ax in axes:
            ax.set_ylim(y_min * 1.05, y_max * 1.05)

        trim_axes(axes, plant_count)

        save_figure(fig, directory, f"plant_production_emissions_{region_name}.png")
