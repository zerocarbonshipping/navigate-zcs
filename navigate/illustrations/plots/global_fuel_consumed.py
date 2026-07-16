# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations.plots._aggregate import merge_fuels_for_plot
from navigate.illustrations.plots._colors import SHORE_POWER_COLOR
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.illustrations.plots._units import get_best_unit_energy


def plot_global_fuel_consumed(manager, directory):
    dateline = manager.get_dateline()

    fig, ax = single_panel()

    fuels = manager.nodes.fuels

    fuel_consumed = manager.profile.get_consumed_energy()
    shore_power = manager.profile.get_shore_power_energy()

    divisor, unit = get_best_unit_energy(np.amax(sum(list(fuel_consumed.values())) + shore_power), default=9)
    fuel_consumed = {fuel_name: consumed / divisor for fuel_name, consumed in fuel_consumed.items()}
    shore_power_scaled = shore_power / divisor

    # merge into required fuels
    values, labels, colors = merge_fuels_for_plot(dateline, fuels, fuel_consumed)

    # add shore power as separate layer
    if np.any(shore_power_scaled > 0.):
        values.append(shore_power_scaled)
        labels.append('Shore Power')
        colors.append(SHORE_POWER_COLOR)

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel('Fuel consumed [{}]'.format(unit))
    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'global_fuel_consumed.png')
