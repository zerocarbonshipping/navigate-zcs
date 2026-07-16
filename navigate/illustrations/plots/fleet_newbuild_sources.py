# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.util import dates_to_years

_SOURCE_COLORS = [CENTER_COLORS_BLUE[3], CENTER_COLORS_RED[3], CENTER_COLORS_GREEN[3]]


def plot_fleet_newbuild_sources(manager, directory) -> None:
    dateline = manager.get_dateline()
    fleets = manager.nodes.fleets

    # time_step_years aligned to dateline by padding the leading zero (np.diff returns length n-1).
    time_step_years = np.zeros(len(dateline))
    time_step_years[1:] = np.diff(dates_to_years(dateline))

    for fleet in fleets.values():

        vessels = fleet.get_vessels()
        profile = fleet.profile

        # Pre-newbuild fleet count = denominator of the count-based newbuild cap; persisted by the
        # cap site so the plot can draw the line with the same multipliers_total the calculation
        # actually used.
        y_existing = profile.get_newbuild_existing_total()

        per_vessel = []
        for vessel in vessels:
            name = vessel.get_name()
            ob = profile.get_orderbook_newbuilds(name)
            ine = profile.get_inertia_newbuilds(name)
            mod = profile.get_modelled_newbuilds(name)
            per_vessel.append((vessel, ob, ine, mod))

        fig, axes = subplot_grid(len(vessels))

        for ax, (vessel, ob, ine, mod) in zip(axes, per_vessel):

            name = vessel.get_name()
            limit = profile.get_newbuild_limit(name)
            # Count-based cap per timestep: limit · y_existing · time_step_years.
            cap_count = limit * y_existing * time_step_years

            plot_stack_with_lines(ax, dateline[1:], [ob[1:], ine[1:], mod[1:]],
                                  ['Orderbook', 'Inertia', 'Modelled'], _SOURCE_COLORS)

            # unassigned vessels default to Scalar(1.0) — skip the line so they aren't visually marked
            if np.any(limit < 1.):
                ax.plot(dateline[1:], cap_count[1:], color='k', lw=2., ls='--', label='Limit')

            ax.set_ylabel('Newbuilds [vessels]')
            ax.set_title(name)
            legend = ax.legend(**LEGEND_OPTIONS)
            format_axes(ax, len(vessels), dateline[1:], legend, y_lim=None)
            ax.set_xlim([dateline[1], dateline[-1]])
            ax.set_ylim([0., None])

        trim_axes(axes, len(vessels))

        save_figure(fig, directory, 'fleet_newbuild_sources_{}.png'.format(fleet.get_name()))
