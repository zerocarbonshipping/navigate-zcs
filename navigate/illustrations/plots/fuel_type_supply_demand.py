# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.fleet.fuel_option import get_fuels_per_fuel_type
from navigate.illustrations.plots._colors import generate_color_dict
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import (
    FUEL_COLOR,
    FUEL_LABEL,
    FUEL_TYPE_LABEL,
    default_label,
)
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.illustrations.plots._units import get_best_unit_energy


def plot_fuel_type_supply_demand(manager, directory):
    dateline = manager.get_dateline()
    # fleets = manager.nodes.fleets
    ports = manager.nodes.ports
    fuels = manager.nodes.fuels
    profile = manager.profile

    fuel_types = [FuelTypeID.OIL, FuelTypeID.METHANE, FuelTypeID.METHANOL, FuelTypeID.AMMONIA]
    fuel_type_to_fuels = get_fuels_per_fuel_type(fuels)

    fig, axes = subplot_grid(len(fuel_types))  # , sharey=True)

    # containers for saving results. Needed for intermediate calculation of optimal unit
    all_values = {}
    all_colors = {}
    all_labels = {}

    all_demand = {}
    all_constrained = {}
    all_fuel_supply = {}

    maximum = 0.

    for fuel_type in fuel_types:

        usable_fuels = fuel_type_to_fuels[fuel_type]
        fuel_spend = {}
        fuel_demand = profile.get_fuel_type_demand(fuel_type)
        fuel_supply = profile.get_production_type_energy()[fuel_type]

        # calculate the total fuel supply and spend
        constrained = True
        for port in ports.values():

            port_profile = port.profile

            for fuel in usable_fuels:

                if not fuel.belongs_to_liquid_market():

                    fuel_name = fuel.get_name()

                    # add fuel supply
                    available = port_profile.get_bunkering_allowed(fuel_name)
                    constraint = port_profile.get_bunker_supply_mass(fuel_name)

                    if constraint is None:

                        if np.any(available):
                            constrained = False
                            break

                    # add fuel spend
                    bunkering = port_profile.get_bunker_energy()

                    if fuel_name in bunkering:

                        if fuel_name in fuel_spend:
                            fuel_spend[fuel_name] += bunkering[fuel_name]
                        else:
                            fuel_spend[fuel_name] = bunkering[fuel_name]

        # plot spend
        values = list(fuel_spend.values())
        fuels_used = {fuel_name: fuels[fuel_name] for fuel_name in fuel_spend}
        colors = list(generate_color_dict(fuels_used, FUEL_COLOR).values())
        labels = [default_label(fuel_name, FUEL_LABEL) for fuel_name in fuel_spend]

        # calculate optimal unit
        maximum = max(maximum, np.amax(fuel_demand))
        if values:
            maximum = max(maximum, max(np.amax(value) for value in values))

        if constrained:
            fuel_supply_max = np.amax(fuel_supply)
            if not np.isinf(fuel_supply_max):
                maximum = max(maximum, fuel_supply_max)

        # save output
        all_values[fuel_type] = values
        all_colors[fuel_type] = colors
        all_labels[fuel_type] = labels

        all_demand[fuel_type] = fuel_demand

        all_constrained[fuel_type] = constrained
        all_fuel_supply[fuel_type] = fuel_supply

    if maximum > 0.:
        divisor, unit = get_best_unit_energy(maximum, default=9)
    else:
        return

    for ax, fuel_type in zip(axes, fuel_types):

        values = [value / divisor for value in all_values[fuel_type]]
        colors = all_colors[fuel_type]
        labels = all_labels[fuel_type]

        fuel_demand = all_demand[fuel_type] / divisor

        constrained = all_constrained[fuel_type]
        fuel_supply = all_fuel_supply[fuel_type] / divisor if constrained else np.zeros_like(fuel_demand)

        patches = []

        if values:
            stack = plot_stack_with_lines(ax, dateline, values, labels, colors, alpha=0.5)
            patches.extend(stack)

        # plot fuel demand
        line_demand = ax.plot(dateline, fuel_demand, label='Demand', ls=(0, (5, 3)), color='r', lw=2)

        patches.extend(line_demand)
        leg_labels = [*labels, 'Demand']

        # if the model is unconstrained for this fuel type, then do not plot supply
        if constrained:
            line_supply = ax.plot(dateline, fuel_supply, label='Supply', ls=(0, (5, 3)), color='b', lw=2)
            patches.extend(line_supply)
            leg_labels.append('Supply')

        ax.set_ylabel('Fuel [{}]'.format(unit))
        ax.set_title(FUEL_TYPE_LABEL[fuel_type])
        legend = ax.legend(patches, leg_labels, **LEGEND_OPTIONS)
        format_axes(ax, len(fuel_types), dateline, legend)

    save_figure(fig, directory, 'fuel_type_supply_demand.png')
