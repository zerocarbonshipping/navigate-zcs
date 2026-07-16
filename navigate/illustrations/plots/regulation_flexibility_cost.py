# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationSchemeID
from navigate.illustrations.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)


def plot_regulation_flexibility_cost(manager, directory):

    dateline = manager.get_dateline()
    regulations = manager.nodes.regulations

    for regulation_name, regulation in regulations.items():

        if not regulation.scheme == RegulationSchemeID.FLEXIBLE:
            continue

        profile = regulation.profile
        remedial_cost = profile.get_remedial_cost()
        flexible_cost = profile.get_flexibility_cost()
        beliefs = profile.get_flexibility_cost_belief()

        fig, ax = single_panel()

        n = len(beliefs)
        alphas = np.linspace(0.2, 0.8, n)

        # belief paths are NaN before their issuance time-step, so plot as-is
        for i, path in enumerate(beliefs):
            label = 'Expected' if i == n - 1 else None
            ax.plot(dateline, path, label=label, color=CENTER_COLORS_BLUE[3], lw=1, alpha=alphas[i])

        ax.plot(dateline, remedial_cost, label='Remedial', color=CENTER_COLORS_RED[3], lw=2.)
        ax.plot(dateline, flexible_cost, label='Flexible', color=CENTER_COLORS_GREEN[3], lw=2.)

        legend = ax.legend()

        ax.set_ylabel("Cost [USD/tCO$_2$-eq.]")
        ax.set_ylim([0., None])

        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend, y_lim=(None, None))

        save_figure(fig, directory, 'regulation_flexibility_cost_{}.png'.format(regulation_name))
