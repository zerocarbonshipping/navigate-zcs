# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._aggregate import to_cumulative
from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_GREY,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import (
    LEGEND_OPTIONS,
)


def _plot_computational_performance(manager, directory, cumulative=False):
    dateline = manager.dateline

    fig, ax = single_panel()

    profile = manager.profile

    # per-step values for all 16 categories, grouped logically
    values = [
        # LP Expected (blue shades)
        profile.get_expected_build_time(),
        profile.get_expected_solve_time(),
        profile.get_expected_transfer_time(),
        # LP Existing (green shades)
        profile.get_existing_build_time(),
        profile.get_existing_solve_time(),
        profile.get_existing_transfer_time(),
        # Fleet decisions (yellow shades)
        profile.get_speed_time(),
        profile.get_retrofit_time(),
        profile.get_fleet_evolution_time(),
        profile.get_producer_evolution_time(),
        # Setup / bookkeeping (grey shades)
        profile.get_temporal_time(),
        profile.get_fleet_state_time(),
        profile.get_overhead_time(),
        # Domain calculations (red shades)
        profile.get_vessel_time(),
        profile.get_fuel_supply_time(),
        profile.get_policy_time(),
        profile.get_profile_agg_time(),
    ]

    labels = [
        # LP Expected
        'Expected (build)', 'Expected (solve)', 'Expected (transfer)',
        # LP Existing
        'Existing (build)', 'Existing (solve)', 'Existing (transfer)',
        # Fleet decisions
        'Speed', 'Retrofit', 'Fleet evolution', 'Producer evolution',
        # Setup / bookkeeping
        'Temporal / expectations', 'Fleet state', 'Overhead',
        # Domain calculations
        'Vessel operations', 'Fuel supply chain', 'Policy / regulation', 'Profile aggregation',
    ]

    colors = [
        # LP Expected -- blue shades (light to dark)
        CENTER_COLORS_BLUE[2], CENTER_COLORS_BLUE[4], CENTER_COLORS_BLUE[6],
        # LP Existing -- green shades
        CENTER_COLORS_GREEN[2], CENTER_COLORS_GREEN[4], CENTER_COLORS_GREEN[6],
        # Fleet decisions -- yellow shades
        CENTER_COLORS_YELLOW[2], CENTER_COLORS_YELLOW[4], CENTER_COLORS_YELLOW[6], CENTER_COLORS_YELLOW[5],
        # Setup / bookkeeping -- grey shades
        CENTER_COLORS_GREY[1], CENTER_COLORS_GREY[3], CENTER_COLORS_GREY[5],
        # Domain calculations -- red shades
        CENTER_COLORS_RED[1], CENTER_COLORS_RED[3], CENTER_COLORS_RED[5], CENTER_COLORS_RED[6],
    ]

    if cumulative:
        values = [to_cumulative(dateline, v) for v in values]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    # total time overlay
    total_cumulative = profile.get_total_time()
    if cumulative:
        ax.plot(dateline, total_cumulative, label='Total', color='k', ls='--', lw=2.)
        ax.set_ylabel('Cumulative computational time [s]')
        suffix = '_cumulative'
    else:
        total_per_step = np.diff(total_cumulative, prepend=0.)
        ax.plot(dateline, total_per_step, label='Total (per step)', color='k', ls='--', lw=2.)
        ax.set_ylabel('Computational time per step [s]')
        suffix = ''

    legend = ax.legend(stack[::-1], labels[::-1], ncol=2, **LEGEND_OPTIONS)

    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'computational_performance{}.png'.format(suffix))


def plot_computational_performance(manager, directory):
    _plot_computational_performance(manager, directory, cumulative=False)


def plot_computational_performance_cumulative(manager, directory):
    _plot_computational_performance(manager, directory, cumulative=True)
