# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._colors import (
    CENTER_COLORS_GREEN,
    CENTER_COLORS_GREY,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import FLEET_LABEL, extract_label


def plot_fleet_speed(manager, directory):
    dateline = manager.dateline

    fleets = manager.nodes.fleets
    relevant_fleets = {fleet_name: fleet for fleet_name, fleet in fleets.items() if fleet.allow_speed_management}

    if not relevant_fleets:
        return

    fig, axes = subplot_grid(len(relevant_fleets))

    for ax, fleet in zip(axes, relevant_fleets.values()):

        profile = fleet.profile
        reference = profile.get_reference_speed()
        minimum = profile.get_minimum_speed()
        maximum = profile.get_maximum_speed()
        actual = profile.get_actual_speed()
        optimum = profile.get_optimal_speed()
        lowest = profile.get_lowest_speed()
        highest = profile.get_highest_speed()

        # there is no speed optimization in the first time-step
        minimum[0] = np.nan
        maximum[0] = np.nan
        actual[0] = np.nan

        ax.fill_between(dateline, minimum, maximum, label='Min/Max', color=CENTER_COLORS_GREY[1], alpha=0.3)
        ax.fill_between(dateline, lowest, highest, label='Distribution', color=CENTER_COLORS_GREY[2], alpha=0.4)
        ax.plot(dateline, reference, label='Reference', color=CENTER_COLORS_GREY[4], ls='--', lw=2.)
        ax.plot(dateline, optimum, label='Optimal', color=CENTER_COLORS_GREEN[3], lw=2)
        ax.plot(dateline, actual, label='Actual', color=CENTER_COLORS_RED[3], lw=2.)

        ax.set_ylabel('Vessel speed [knots]')
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        leg = ax.legend()
        format_axes(ax, len(relevant_fleets), dateline, legend=leg)

    trim_axes(axes, len(relevant_fleets))

    save_figure(fig, directory, 'fleet_speed.png')
