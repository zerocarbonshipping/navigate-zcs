# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.enum_ import RegulationSchemeID
from navigate.output.plots._colors import (
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)


def plot_regulation_flexibility_cost(manager, directory):

    dateline = manager.dateline
    regulations = manager.nodes.regulations

    for regulation_name, regulation in regulations.items():

        if not regulation.scheme == RegulationSchemeID.FLEXIBLE:
            continue

        profile = regulation.profile
        remedial_cost = profile.get_remedial_cost()
        flexible_cost = profile.get_flexibility_cost()

        fig, ax = single_panel()

        ax.plot(dateline, remedial_cost, label='Remedial', color=CENTER_COLORS_RED[3], lw=2.)
        ax.plot(dateline, flexible_cost, label='Flexible', color=CENTER_COLORS_GREEN[3], lw=2.)

        legend = ax.legend()

        ax.set_ylabel("Cost [USD/tCO$_2$-eq.]")
        ax.set_ylim([0., None])

        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend, y_lim=(None, None))

        save_figure(fig, directory, 'regulation_flexibility_cost_{}.png'.format(regulation_name))
