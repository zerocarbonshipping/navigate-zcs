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
    default_label,
)
from navigate.output.plots._units import get_best_unit_mass
from navigate.util import divide_nonzero


def plot_port_bunker_supply(manager, directory):
    dateline = manager.dateline

    ports = manager.nodes.ports
    fuels = manager.nodes.fuels
    fuels = {fuel_name: fuel for fuel_name, fuel in fuels.items() if not fuel.belongs_to_liquid_market()}

    if not fuels:
        return

    colors = generate_color_dict(fuels, FUEL_COLOR)

    for port_name, port in ports.items():

        fig, axes = subplot_grid(len(fuels))

        profile = port.profile

        for ax, fuel_name in zip(axes, fuels):

            bunkered = profile.get_bunker_mass(fuel_name)
            supply = profile.get_bunker_supply_mass(fuel_name)
            limit = profile.get_bunkering_limit_mass(fuel_name)

            limit = np.where(np.isinf(limit), np.nan, limit)

            if np.all(np.isnan(limit)):
                max_limit = 0.
            else:
                max_limit = np.nanmax(limit)

            maximum = max(np.amax(bunkered), np.amax(supply), max_limit)
            divisor, unit = get_best_unit_mass(maximum)

            plot_stack_with_lines(ax, dateline,
                                  [divide_nonzero(bunkered, divisor)],
                                  ['Bunkered'],
                                  [colors[fuel_name]], alpha=0.7)

            ax.plot(dateline, divide_nonzero(supply, divisor), 'k', label='Supply')

            if np.any(np.isfinite(limit)):
                ax.plot(dateline, divide_nonzero(limit, divisor), 'k', label='Infrastructure', ls='--')

            ax.set_ylabel('Bunkering [{}]'.format(unit))
            ax.set_title(default_label(fuel_name, FUEL_LABEL))
            legend = ax.legend()
            format_axes(ax, len(fuels), dateline, legend)

        trim_axes(axes, len(fuels))

        save_figure(fig, directory, 'port_bunker_supply_{}.png'.format(port_name))
