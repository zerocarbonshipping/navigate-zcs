# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations.plots._aggregate import to_cumulative
from navigate.illustrations.plots._colors import (
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.illustrations.plots._units import get_best_unit_cost


def _plot_global_fuel_related_expenses(manager, directory, cumulative=False):
    dateline = manager.get_dateline()

    fig, ax = single_panel()

    profile = manager.profile
    fuel_expenses = profile.get_total_fuel_expenses()
    levy_expenses = profile.get_total_levy_expenses()
    regulation_expenses = profile.get_regulation_expenses()

    values = [fuel_expenses, levy_expenses, regulation_expenses]

    if cumulative:
        values = [to_cumulative(dateline, v) for v in values]

    divisor, unit = get_best_unit_cost(np.amax(sum(values)), rate=not cumulative)

    values = [v / divisor for v in values]
    labels = ['Fuel', 'Levy', 'Regulation']
    colors = [CENTER_COLORS_GREEN[3], CENTER_COLORS_YELLOW[3], CENTER_COLORS_RED[3]]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    if cumulative:
        ax.set_ylabel('Cumulative expenses [{}]'.format(unit))
        suffix = '_cumulative'
    else:
        ax.set_ylabel('Expenses [{}]'.format(unit))
        suffix = ''

    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'global_fuel_related_expenses{}.png'.format(suffix))


def plot_global_fuel_related_expenses(manager, directory):
    _plot_global_fuel_related_expenses(manager, directory, cumulative=False)


def plot_global_fuel_related_expenses_cumulative(manager, directory):
    _plot_global_fuel_related_expenses(manager, directory, cumulative=True)
