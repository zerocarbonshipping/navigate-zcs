# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.illustrations._illu_util import trim_axes
from navigate.illustrations.plots._colors import SHORE_POWER_COLOR
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.illustrations.plots._labels import FLEET_LABEL, extract_label
from navigate.util import divide_nonzero


def plot_fleet_shore_power_share(manager, directory):
    dateline = manager.get_dateline()

    fleets = manager.nodes.fleets
    fig, axes = subplot_grid(len(fleets), sharey=True)

    for ax, fleet in zip(axes, fleets.values()):

        fleet_profile = fleet.profile
        shore_power = fleet_profile.get_shore_power_energy()
        port_energy = fleet_profile.get_total_energy_port()

        shore_power_share = divide_nonzero(shore_power, port_energy) * 100.

        ax.fill_between(dateline, shore_power_share, color=SHORE_POWER_COLOR, alpha=0.6)
        ax.plot(dateline, shore_power_share, color=SHORE_POWER_COLOR, lw=2.5)

        ax.set_ylabel('Shore power share [%]')
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        format_axes(ax, len(fleets), dateline)

    for ax in axes:
        ax.set_ylim(bottom=0.)

    trim_axes(axes, len(fleets))

    save_figure(fig, directory, 'fleet_shore_power_share.png')
