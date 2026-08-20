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
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FLEET_LABEL, extract_label
from navigate.illustrations.plots._style import LEGEND_OPTIONS


def plot_fleet_energy_saving(manager, directory):
    dateline = manager.get_dateline()

    fleets = manager.nodes.fleets

    fig, axes = subplot_grid(len(fleets), sharey=False)

    min_saving = 0.
    max_saving = 0.

    for ax, fleet in zip(axes, fleets.values()):

        fleet_profile = fleet.profile

        saving_op = fleet_profile.get_operational_energy_intensity_saving() * 100.
        saving_tech = fleet_profile.get_technology_energy_intensity_saving() * 100.
        saving = fleet_profile.get_energy_intensity_saving() * 100.

        min_saving = min(min_saving, np.amin(saving_tech), np.amin(saving_op), np.amin(saving))
        max_saving = max(max_saving, np.amax(saving_tech), np.amax(saving_op), np.amax(saving))

        ax.plot(dateline, saving_op, label='Operational', color=CENTER_COLORS_BLUE[3], lw=2)
        ax.plot(dateline, saving_tech, label='Technology', color=CENTER_COLORS_RED[3], lw=2)
        ax.plot(dateline, saving, label='Total', color=CENTER_COLORS_GREEN[3], lw=2)

        # add zero-line in case of negative savings from increased speed
        ax.plot(dateline, np.zeros_like(dateline, dtype=np.float64), color='k', lw=2)

        ax.set_ylabel('Energy Saving [%]')
        ax.set_title(extract_label(fleet, FLEET_LABEL))

        legend = ax.legend(**LEGEND_OPTIONS)
        format_axes(ax, len(fleets), dateline, legend, y_lim=None)

    trim_axes(axes, len(fleets))

    for ax in axes:
        ax.set_ylim((min_saving - 2., max_saving + 2.))

    save_figure(fig, directory, 'fleet_energy_saving.png')
