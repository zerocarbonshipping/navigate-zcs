# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_RED,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FUEL_LABEL, extract_label
from navigate.illustrations.plots._units import get_best_unit_energy
from navigate.util import divide_nonzero


def plot_fuel_supply_demand_expectation(manager, directory):

    dateline = manager.get_dateline()
    fuels = manager.nodes.fuels

    profile = manager.profile
    demand_expectation = profile.get_demand_expectation()
    supply_expectation = profile.get_supply_expectation()

    fig, axes = subplot_grid(len(fuels))

    for ax, (fuel_name, fuel) in zip(axes, fuels.items()):

        lhv = fuel.lower_heating_value.get()

        demands = demand_expectation[fuel_name]
        supplies = supply_expectation[fuel_name]
        demand_actual = profile.get_consumed_energy(fuel_name)
        supply_actual = profile.get_production_energy(fuel_name)

        # convert to energy
        demands = [d * lhv for d in demands]
        supplies = [s * lhv for s in supplies]

        # replace infinity by nan
        supplies = [np.where(~np.isinf(s), s, np.nan) for s in supplies]

        maximum = max(max(*[np.nanmax(d) for d in demands]),
                      max(*[np.nanmax(s) if np.any(np.isfinite(s)) else 0. for s in supplies]),
                      np.amax(demand_actual),
                      np.amax(supply_actual))

        divisor, unit = get_best_unit_energy(maximum, default=9)

        n = len(demands)
        alphas = np.linspace(0.2, 0.8, n)

        label_demand = None
        label_supply = None

        for i, (demand, supply) in enumerate(zip(demands, supplies)):

            # adding label to the last demand
            # to get the one with highest alpha
            # for visibility in legend
            if i == n - 1:
                label_demand = 'Demand'
                label_supply = 'Supply'

            _demand = np.full_like(demand, np.nan)
            _supply = np.full_like(supply, np.nan)
            _demand[i:] = demand[i:]
            _supply[i:] = supply[i:]

            ax.plot(dateline, divide_nonzero(_demand, divisor),
                    label=label_demand,
                    color=CENTER_COLORS_RED[2],
                    lw=1,
                    alpha=alphas[i])
            ax.plot(dateline, divide_nonzero(_supply, divisor),
                    label=label_supply,
                    color=CENTER_COLORS_BLUE[2],
                    lw=1,
                    alpha=alphas[i])

        ax.plot(dateline, divide_nonzero(demand_actual, divisor), label='Consumed', color=CENTER_COLORS_RED[2], lw=2)
        ax.plot(dateline, divide_nonzero(supply_actual, divisor), label='Produced', color=CENTER_COLORS_BLUE[2], lw=2, ls='--')

        ax.set_ylabel('Fuel energy [{}]'.format(unit))
        ax.set_title(extract_label(fuel, FUEL_LABEL))
        leg = ax.legend()
        format_axes(ax, len(fuels), dateline, legend=leg)

    trim_axes(axes, len(fuels))

    save_figure(fig, directory, 'fuel_supply_demand_expectation.png')
