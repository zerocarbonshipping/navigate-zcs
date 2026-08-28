# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import (
    FLEET_LABEL,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_ORDER,
    extract_label,
)
from navigate.util import TOLERANCE, collapse_tuple_dict, dates_to_years


def _vessel_series_by_fuel_type(series, vessel_map):
    """Flat (values, colors) per vessel, in canonical fuel-type order, near-zero dropped."""

    order = {ft: i for i, ft in enumerate(FUEL_TYPE_ORDER)}

    names = [name for name, values in series.items()
             if not np.all(np.abs(values) < TOLERANCE) and vessel_map[name].fuel_type in order]
    names.sort(key=lambda name: order[vessel_map[name].fuel_type])

    return ([series[name] for name in names],
            [FUEL_TYPE_COLOR[vessel_map[name].fuel_type] for name in names])


def plot_fleet_conversions_cumulative(manager, directory):
    dateline = manager.dateline
    fleets = manager.nodes.fleets

    fuel_conversions = {fleet_name: fleet.profile.get_fuel_conversions()
                        for fleet_name, fleet in fleets.items()
                        if fleet.can_fuel_convert()}

    if not fuel_conversions:
        return

    fig, axes = subplot_grid(len(fuel_conversions))

    count = 0
    for ax, (fleet_name, conversions) in zip(axes, fuel_conversions.items()):

        # used for trimming
        count += 1

        vessel_map = {vessel.name: vessel for vessel in fleets[fleet_name].vessels}

        conversions_from = collapse_tuple_dict(conversions, key1=True)
        conversions_from = {key: -conversion for key, conversion in conversions_from.items()}
        conversions_to = collapse_tuple_dict(conversions, key2=True)

        values_from, colors_from = _vessel_series_by_fuel_type(conversions_from, vessel_map)
        values_to, colors_to = _vessel_series_by_fuel_type(conversions_to, vessel_map)

        dt = np.diff(dates_to_years(dateline))
        values_from = [np.cumsum(v[1:] * dt) for v in values_from]
        values_to = [np.cumsum(v[1:] * dt) for v in values_to]

        # plot stacks
        plot_stack_with_lines(ax, dateline[1:], values_from, [], colors_from)
        plot_stack_with_lines(ax, dateline[1:], values_to, [], colors_to)

        # plot zero line
        ax.plot([dateline[1], dateline[-1]], [0., 0.], c='k', lw=2)

        ax.set_ylabel('Number of vessels')
        ax.set_title(extract_label(fleets[fleet_name], FLEET_LABEL))

        format_axes(ax, len(fuel_conversions), dateline[1:], legend=None, y_lim=(None, None))

    trim_axes(axes, count)

    save_figure(fig, directory, 'fleet_conversions_cumulative.png')
