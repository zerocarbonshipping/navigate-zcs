# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import matplotlib.patches as mpatches
import numpy as np

from navigate.core.misc import TOLERANCE
from navigate.output.plots._aggregate import unpack_fuel_type_series
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import find_best_metric_prefix
from navigate.util import (
    collapse_tuple_dict,
    dates_to_years,
    divide_nonzero,
)


def _plot_global_power_converted(manager, directory, cumulative=False):
    dateline = manager.get_dateline()

    fig, ax = single_panel()

    converted_power = manager.profile.get_fuel_converted_power()
    converted_power = {key: value for key, value in converted_power.items() if np.any(np.abs(value) > TOLERANCE)}

    divisor, prefix = find_best_metric_prefix(np.amax(np.sum(list(converted_power.values()))), default=6)
    converted_power = {key: divide_nonzero(power, divisor) for key, power in converted_power.items()}
    unit = '{}W'.format(prefix)

    conversions_from = collapse_tuple_dict(converted_power, key1=True)
    conversions_from = {key: -conversion for key, conversion in conversions_from.items()}
    conversions_to = collapse_tuple_dict(converted_power, key2=True)

    values_from, labels_from, colors_from = unpack_fuel_type_series(conversions_from)
    values_to, labels_to, colors_to = unpack_fuel_type_series(conversions_to)

    if cumulative:
        dt = np.diff(dates_to_years(dateline))
        values_from = [np.cumsum(v[1:] * dt) for v in values_from]
        values_to = [np.cumsum(v[1:] * dt) for v in values_to]

    else:
        values_from = [v[1:] for v in values_from]
        values_to = [v[1:] for v in values_to]

    # plot stacks
    stack = plot_stack_with_lines(ax, dateline[1:], values_from, labels_from, colors_from)
    stack.append(plot_stack_with_lines(ax, dateline[1:], values_to, labels_to, colors_to))

    # create proxy artist for legend
    unique_labels = [*labels_from]
    unique_colors = [*colors_from]

    for label, color in zip(labels_to, colors_to):

        if label not in unique_labels:

            unique_labels.append(label)
            unique_colors.append(color)

    # plot zero line
    ax.plot([dateline[1], dateline[-1]], [0., 0.], c='k', lw=2)

    ax.set_ylabel('Converted power [{}]'.format(unit))

    patches = [mpatches.Patch(color=color, label=label) for label, color in zip(unique_labels, unique_colors)]
    legend = ax.legend(handles=patches, **LEGEND_OPTIONS)

    format_axes(ax, 1, dateline[1:], legend, y_lim=(None, None))

    suffix = '_cumulative' if cumulative else ''

    save_figure(fig, directory, 'global_power_converted{}.png'.format(suffix))


def plot_global_power_converted_cumulative(manager, directory):
    _plot_global_power_converted(manager, directory, cumulative=True)
