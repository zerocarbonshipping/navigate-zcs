# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._aggregate import (
    merge_fuels_for_plot,
    remove_below_threshold,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)
from navigate.output.plots._labels import FUEL_TYPE_LABEL
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_energy


def plot_engine_fuel_consumed(manager, directory):
    dateline = manager.get_dateline()

    fuels = manager.nodes.fuels
    engine_fuel_consumed = manager.profile.get_converter_energy()

    for consumed in engine_fuel_consumed.values():
        remove_below_threshold(consumed, 1.)

    engine_fuel_consumed = {fuel_type: consumed for fuel_type, consumed in engine_fuel_consumed.items() if consumed}

    max_ = max(np.amax(sum(list(consumed.values()))) for consumed in engine_fuel_consumed.values())
    divisor, unit = get_best_unit_energy(max_, default=9)

    fig, axes = subplot_grid(len(engine_fuel_consumed))

    for ax, fuel_type in zip(axes, engine_fuel_consumed):

        fuel_consumed = engine_fuel_consumed[fuel_type]
        fuel_consumed = {fuel_name: consumed / divisor for fuel_name, consumed in fuel_consumed.items()}

        # merge into required fuels
        values, labels, colors = merge_fuels_for_plot(dateline, fuels, fuel_consumed)

        legend = None
        if values:
            stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

            legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)

        ax.set_ylabel('Fuel consumed [{}]'.format(unit))

        ax.set_title('{} vessels'.format(FUEL_TYPE_LABEL[fuel_type]))
        format_axes(ax, len(engine_fuel_consumed), dateline, legend)

    trim_axes(axes, len(engine_fuel_consumed))

    save_figure(fig, directory, 'engine_fuel_consumed.png')
