# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._aggregate import merge_fuels_for_plot
from navigate.output.plots._colors import SHORE_POWER_COLOR
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import FLEET_LABEL, extract_label
from navigate.output.plots._units import get_best_unit_energy


def plot_fleet_fuel_consumed(manager, directory):
    dateline = manager.get_dateline()

    fuels = manager.nodes.fuels
    fleets = manager.nodes.fleets
    fig, axes = subplot_grid(len(fleets), sharex=True)

    # cumulate fuel spent over all fleets
    for ax, fleet in zip(axes, fleets.values()):

        fleet_profile = fleet.profile
        fuel_demand = fleet_profile.get_consumed_energy()
        shore_power = fleet_profile.get_shore_power_energy()

        divisor, unit = get_best_unit_energy(np.amax(sum(list(fuel_demand.values())) + shore_power), default=9)
        fuel_demand = {fuel_name: demand / divisor for fuel_name, demand in fuel_demand.items()}
        shore_power_scaled = shore_power / divisor

        # merge into required fuels
        values, labels, colors = merge_fuels_for_plot(dateline, fuels, fuel_demand)

        # add shore power as separate layer
        if np.any(shore_power_scaled > 0.):
            values.append(shore_power_scaled)
            labels.append('Shore Power')
            colors.append(SHORE_POWER_COLOR)

        plot_stack_with_lines(ax, dateline, values, labels, colors)

        ax.set_ylabel('Fuel consumed [{}]'.format(unit))
        ax.set_title(extract_label(fleet, FLEET_LABEL))

        format_axes(ax, len(fleets), dateline)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_fuel_consumed.png')
