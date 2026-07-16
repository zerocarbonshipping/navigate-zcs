# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations.plots._aggregate import (
    remove_below_threshold,
    unpack_fuel_type_series,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.illustrations.plots._labels import FUEL_TYPE_ORDER
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.illustrations.plots._units import find_best_metric_prefix


def plot_global_installed_power(manager, directory):
    dateline = manager.get_dateline()

    fig, ax = single_panel()

    engine_power = {ft: manager.profile.get_installed_power(ft) for ft in FUEL_TYPE_ORDER}

    remove_below_threshold(engine_power, 1.)

    divisor, prefix = find_best_metric_prefix(np.amax(sum(list(engine_power.values()))), default=6)
    engine_power = {fuel_type: power / divisor for fuel_type, power in engine_power.items()}
    unit = '{}W'.format(prefix)

    values, labels, colors = unpack_fuel_type_series(engine_power)

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel('Installed power [{}]'.format(unit))
    legend = ax.legend(stack[::-1], labels[::-1],  **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'global_installed_power.png')
