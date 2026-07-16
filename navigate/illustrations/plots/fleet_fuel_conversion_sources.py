# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FUEL_TYPE_COLOR
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.util import dates_to_years, divide_nonzero


def _plot_fleet_fuel_conversion_sources(manager, directory, normalize: bool = False) -> None:
    dateline = manager.get_dateline()
    fleets = manager.nodes.fleets

    for fleet in fleets.values():

        if not fleet.can_fuel_convert():
            continue

        profile = fleet.profile
        vessel_map = {vessel.get_name(): vessel for vessel in fleet.get_vessels()}

        pairs = fleet.get_fuel_conversion_cost_pairs()
        if not pairs:
            continue

        # time_step_years aligned to dateline by padding the leading zero (np.diff returns length n-1).
        time_step_years = np.diff(dates_to_years(dateline))

        # Pre-newbuild fleet total — `existing_vessels` would offset the cap line by same-timestep newbuilds.
        existing_total = profile.get_fuel_conversion_existing_total()

        fig, axes = subplot_grid(len(pairs))

        for ax, (name_from, name_to) in zip(axes, pairs):
            count = profile.get_fuel_conversions(name_from, name_to)
            limit_pair = profile.get_fuel_conversion_limit(name_from, name_to)
            color = FUEL_TYPE_COLOR[vessel_map[name_to].fuel_type]

            # Per-pair cap: per-pair conversions ≤ limit_pair × time_step_years × existing_total.
            limit_share = np.zeros(len(dateline))
            limit_share[1:] = limit_pair[1:] * time_step_years

            if normalize:
                value = divide_nonzero(count, existing_total)
                limit = limit_share
                y_label = 'Conversion share of fleet [-]'
            else:
                value = count
                limit = limit_share * existing_total
                y_label = 'Conversions [vessels]'

            plot_stack_with_lines(ax, dateline[1:], [value[1:]], ['Conversions'], [color])

            # drop the limit line only when the per-pair cap is vacuous (== 1 over the run)
            if np.any(limit_pair[1:] < 1. - 1e-12):
                ax.plot(dateline[1:], limit[1:], color='k', lw=2., ls=':', label='Limit')

            ax.set_ylabel(y_label)
            ax.set_title('{}  ->  {}'.format(name_from, name_to))
            legend = ax.legend(**LEGEND_OPTIONS)
            format_axes(ax, len(pairs), dateline[1:], legend, y_lim=None)
            ax.set_xlim([dateline[1], dateline[-1]])

            ax.set_ylim([0., None])

        trim_axes(axes, len(pairs))

        suffix = '_normalized' if normalize else ''
        save_figure(fig, directory, 'fleet_fuel_conversion_sources{}_{}.png'.format(suffix, fleet.get_name()))


def plot_fleet_fuel_conversion_sources(manager, directory):
    _plot_fleet_fuel_conversion_sources(manager, directory, normalize=False)


def plot_fleet_fuel_conversion_sources_normalized(manager, directory):
    _plot_fleet_fuel_conversion_sources(manager, directory, normalize=True)
