# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.output.plots._colors import SHORE_POWER_COLOR
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.util import divide_nonzero


def plot_global_shore_power_share(manager, directory):
    dateline = manager.dateline

    fig, ax = single_panel()

    profile = manager.profile
    shore_power = profile.get_shore_power_energy()
    port_energy = profile.get_total_energy_port()

    shore_power_share = divide_nonzero(shore_power, port_energy) * 100.

    ax.fill_between(dateline, shore_power_share, color=SHORE_POWER_COLOR, alpha=0.6)
    ax.plot(dateline, shore_power_share, color=SHORE_POWER_COLOR, lw=2.5)

    ax.set_ylabel('Shore power share [%]')
    ax.set_ylim(bottom=0.)
    format_axes(ax, 1, dateline)

    save_figure(fig, directory, 'global_shore_power_share.png')
