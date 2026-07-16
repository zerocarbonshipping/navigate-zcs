# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FLEET_LABEL, extract_label


def plot_fleet_emission_intensity(manager, directory):
    dateline = manager.get_dateline()
    fleets = manager.nodes.fleets

    fig, axes = subplot_grid(len(fleets))

    for ax, fleet in zip(axes, fleets.values()):

        intensity = fleet.profile.get_intensity_total_equivalent_WTW()

        ax.plot(dateline, intensity, label='Model', color='k')

        ax.set_ylabel('WTW CO$_2$-eq. intensity [kg/GJ/year]')
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        format_axes(ax, len(fleets), dateline)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_emission_intensity.png')
