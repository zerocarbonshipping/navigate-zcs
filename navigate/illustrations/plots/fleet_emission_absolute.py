# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FLEET_LABEL, extract_label
from navigate.illustrations.plots._style import LEGEND_OPTIONS
from navigate.illustrations.plots._units import get_best_unit_mass


def plot_fleet_emission_absolute(manager, directory):
    dateline = manager.get_dateline()
    fleets = manager.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    for ax, fleet in zip(axes, fleets.values()):

        profile = fleet.profile
        WTW = profile.get_total_equivalent_WTW()

        divisor, unit = get_best_unit_mass(WTW.max())
        WTW /= divisor

        ax.plot(dateline, WTW, label='WTW', color='k')

        ax.set_ylabel('WTW CO$_2$-eq. [{}]'.format(unit))
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        legend = ax.legend(**LEGEND_OPTIONS)
        format_axes(ax, len(fleets), dateline, legend)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_emission_absolute.png')
