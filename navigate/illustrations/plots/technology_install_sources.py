# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._colors import CENTER_COLORS_BLUE
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.util import dates_to_years, divide_nonzero


def _plot_technology_install_sources(manager, directory, normalize: bool = False) -> None:
    dateline = manager.get_dateline()
    fleets = manager.nodes.fleets

    for fleet in fleets.values():

        if not fleet.technologies:
            continue

        profile = fleet.profile

        # Only plot technologies whose newbuild cap binds somewhere along the timeline.
        # Defaults are Scalar(1.0) — `< 1 - eps` filters them out so unconstrained technologies aren't drawn.
        technologies_with_cap = []
        for technology in fleet.technologies:
            limit = profile.get_newbuild_technology_limit(technology.get_name())
            if np.any(limit < 1. - 1e-12):
                technologies_with_cap.append(technology)

        if not technologies_with_cap:
            continue

        time_step_years = np.diff(dates_to_years(dateline))
        y_existing = profile.get_newbuild_existing_total()
        vessels = fleet.get_vessels()
        colors = [CENTER_COLORS_BLUE[(3 + i) % len(CENTER_COLORS_BLUE)] for i in range(len(vessels))]

        fig, axes = subplot_grid(len(technologies_with_cap))

        for ax, technology in zip(axes, technologies_with_cap):

            technology_name = technology.get_name()
            limit = profile.get_newbuild_technology_limit(technology_name)

            # Per-technology cap aligned to dateline by padding the leading zero (np.diff returns length n-1).
            limit_share = np.zeros(len(dateline))
            limit_share[1:] = limit[1:] * time_step_years

            stack_values = []
            stack_labels = []
            for vessel in vessels:
                share = profile.get_newbuild_technology_uptake(vessel.get_name(), technology_name)
                count = profile.get_newbuilds(vessel.get_name())
                stack_values.append(share * count)
                stack_labels.append(vessel.get_name())

            if normalize:
                values_n = [divide_nonzero(v, y_existing) for v in stack_values]
                limit_line = limit_share
                y_label = 'Newbuild install share of fleet [-]'
            else:
                values_n = stack_values
                limit_line = limit_share * y_existing
                y_label = 'Installs [vessels]'

            sliced = [v[1:] for v in values_n]
            plot_stack_with_lines(ax, dateline[1:], sliced, stack_labels, colors[:len(vessels)])

            ax.plot(dateline[1:], limit_line[1:], color='k', lw=2., ls=':', label='Limit')

            ax.set_ylabel(y_label)
            ax.set_title(technology_name)
            legend = ax.legend(**LEGEND_OPTIONS)
            format_axes(ax, len(technologies_with_cap), dateline[1:], legend, y_lim=None)
            ax.set_xlim([dateline[1], dateline[-1]])

            ax.set_ylim([0., None])

        trim_axes(axes, len(technologies_with_cap))

        suffix = '_normalized' if normalize else ''
        save_figure(fig, directory, 'technology_install_sources{}_{}.png'.format(suffix, fleet.get_name()))


def plot_technology_install_sources(manager, directory):
    _plot_technology_install_sources(manager, directory, normalize=False)


def plot_technology_install_sources_normalized(manager, directory):
    _plot_technology_install_sources(manager, directory, normalize=True)
