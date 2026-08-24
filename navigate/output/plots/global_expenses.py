# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._aggregate import to_cumulative
from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_cost


def _plot_global_expenses(manager, directory, cumulative=False):
    dateline = manager.get_dateline()

    fig, ax = single_panel()

    profile = manager.profile
    vessel_expenses = profile.get_vessel_expenses()
    conversion_expenses = profile.get_fuel_conversion_expenses()
    technology_expenses = profile.get_technology_expenses()
    fuel_expenses = profile.get_total_fuel_expenses()
    policy_expenses = profile.get_total_levy_expenses() + profile.get_regulation_expenses()

    values = [vessel_expenses,
              conversion_expenses,
              technology_expenses,
              fuel_expenses,
              policy_expenses]

    if cumulative:
        values = [to_cumulative(dateline, v) for v in values]

    divisor, unit = get_best_unit_cost(np.amax(sum(values)), rate=not cumulative)
    values = [v / divisor for v in values]
    labels = ['Vessel',
              'Fuel conversion',
              'Technology',
              'Fuel',
              'Policy']
    colors = [CENTER_COLORS_BLUE[3],
              CENTER_COLORS_BLUE[2],
              CENTER_COLORS_RED[3],
              CENTER_COLORS_GREEN[3],
              CENTER_COLORS_YELLOW[3]]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    if cumulative:
        ax.set_ylabel('Cumulative expenses [{}]'.format(unit))
        suffix = '_cumulative'
    else:
        ax.set_ylabel('Expenses [{}]'.format(unit))
        suffix = ''

    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'global_expenses{}.png'.format(suffix))


def plot_global_expenses(manager, directory):
    _plot_global_expenses(manager, directory, cumulative=False)


def plot_global_expenses_cumulative(manager, directory):
    _plot_global_expenses(manager, directory, cumulative=True)
