# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.enum_ import EnergyDemandTypeID
from navigate.illustrations.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)


def plot_global_energy_saving(manager, directory):
    dateline = manager.get_dateline()

    fig, axes = subplot_grid(6, sharey=True)

    profile = manager.profile
    propulsion_saving = profile.get_saving(EnergyDemandTypeID.PROPULSION) * 100.
    electrical_saving = profile.get_saving(EnergyDemandTypeID.ELECTRICAL) * 100.
    heat_saving = profile.get_saving(EnergyDemandTypeID.HEAT) * 100.
    technology_saving = profile.get_technology_energy_intensity_saving() * 100.
    operational_saving = profile.get_operational_energy_intensity_saving() * 100.
    total_saving = profile.get_energy_intensity_saving() * 100.

    max_value = max(propulsion_saving.max(), electrical_saving.max(), heat_saving.max(),
                    technology_saving.max(), operational_saving.max(), total_saving.max())

    values = [propulsion_saving, electrical_saving, heat_saving, technology_saving, operational_saving, total_saving]
    titles = ['Propulsion', 'Electrical', 'Heat', 'Technology', 'Operational', 'Total']
    colors = [CENTER_COLORS_BLUE[2], CENTER_COLORS_GREEN[2], CENTER_COLORS_RED[2],
              CENTER_COLORS_GREEN[3], CENTER_COLORS_YELLOW[3], CENTER_COLORS_BLUE[4]]

    for ax, value, title, color in zip(axes, values, titles, colors):
        ax.plot(dateline, value, color=color, lw=5)

        ax.set_title(title)
        ax.set_ylabel('Energy saving [%]')
        format_axes(ax, 6, dateline, y_lim=(None, None))

    if max_value > 0.:

        for ax in axes:
            ax.set_ylim([0., 1.1 * max_value])

    save_figure(fig, directory, 'global_energy_saving.png')
