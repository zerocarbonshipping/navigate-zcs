# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations.plots._aggregate import unpack_fuel_type_series
from navigate.illustrations.plots._colors import SHORE_POWER_COLOR
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.illustrations.plots._labels import FUEL_TYPE_ORDER
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.illustrations.plots._units import get_best_unit_energy


def plot_global_fuel_type_consumed(manager, directory):
    dateline = manager.get_dateline()

    fig, ax = single_panel()

    fuel_type_consumed = manager.profile.get_fuel_type_energy()
    fuel_type_consumed = {ft: fuel_type_consumed[ft] for ft in FUEL_TYPE_ORDER}

    shore_power = manager.profile.get_shore_power_energy()

    divisor, unit = get_best_unit_energy(np.amax(sum(list(fuel_type_consumed.values())) + shore_power), default=9)
    fuel_type_consumed = {fuel_type: demand / divisor for fuel_type, demand in fuel_type_consumed.items()}
    shore_power_scaled = shore_power / divisor

    # merge into required fuels
    values, labels, colors = unpack_fuel_type_series(fuel_type_consumed)

    # add shore power as separate layer
    if np.any(shore_power_scaled > 0.):
        values.append(shore_power_scaled)
        labels.append('Shore Power')
        colors.append(SHORE_POWER_COLOR)

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel('Fuel consumed [{}]'.format(unit))
    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'global_fuel_type_consumed.png')
