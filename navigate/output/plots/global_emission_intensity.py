# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)


def plot_global_emission_intensity(manager, directory):
    dateline = manager.dateline

    fig, ax = single_panel()

    profile = manager.profile
    intensity = profile.get_intensity_total_equivalent_WTW()

    ax.plot(dateline, intensity, color='k')

    ax.set_ylabel('WTW CO$_2$-eq. intensity [kg/GJ/year]')
    format_axes(ax, 1, dateline)

    save_figure(fig, directory, 'global_emission_intensity.png')
