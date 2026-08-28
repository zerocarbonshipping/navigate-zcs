# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_mass


def plot_global_emission_absolute(manager, directory):
    dateline = manager.dateline

    fig, ax = single_panel()

    profile = manager.profile
    wtw = profile.get_total_equivalent_wtw()

    divisor, unit = get_best_unit_mass(wtw.max())
    wtw /= divisor

    ax.plot(dateline, wtw, label='WTW', color='k')

    ax.set_ylabel('WTW CO$_2$-eq. [{}]'.format(unit))
    legend = ax.legend(**LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, 'global_emission_absolute.png')
