# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)
from navigate.output.plots._labels import (
    FUEL_COLOR,
    FUEL_LABEL,
    extract_label,
)
from navigate.output.plots._units import get_best_unit_energy
from navigate.util import divide_nonzero


def plot_fuel_supply_demand(manager, directory):
    dateline = manager.dateline

    fuels = manager.nodes.fuels
    profile = manager.profile

    fig, axes = subplot_grid(len(fuels))

    colors = generate_color_dict(fuels, FUEL_COLOR)

    for ax, (fuel_name, fuel) in zip(axes, fuels.items()):

        consumed = profile.get_consumed_energy(fuel_name)

        if not fuel.belongs_to_liquid_market():
            production = profile.get_production_energy(fuel_name)
        else:
            production = np.zeros_like(consumed)

        maximum = max(np.amax(consumed), np.amax(production))
        divisor, unit = get_best_unit_energy(maximum, default=9)

        plot_stack_with_lines(ax, dateline, [divide_nonzero(consumed, divisor)], ['Consumed'], [colors[fuel_name]], alpha=0.7)

        if not fuel.belongs_to_liquid_market():

            ax.plot(dateline, divide_nonzero(production, divisor), 'k', label='Produced')

        ax.set_ylabel('Fuel [{}]'.format(unit))
        ax.set_title(extract_label(fuel, FUEL_LABEL))
        legend = ax.legend()
        format_axes(ax, len(fuels), dateline, legend)

    trim_axes(axes, len(fuels))

    save_figure(fig, directory, 'fuel_supply_demand.png')
