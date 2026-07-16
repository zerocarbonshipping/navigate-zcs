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
from navigate.illustrations.plots._style import (
    LEGEND_OPTIONS,
)


def plot_regulation_offsetting_cost(manager, directory):

    dateline = manager.get_dateline()
    regulations = manager.nodes.regulations
    model_definition = manager.general_nodes.model_definition

    offsetting_enabled = model_definition.get_enable_offsetting()
    if not offsetting_enabled:
        return

    offsetting_cost_attr = model_definition.get_offsetting_cost()
    offsetting_cost_value = offsetting_cost_attr.get() if offsetting_cost_attr is not None else None

    for regulation_name, regulation in regulations.items():

        if not regulation.scheme == RegulationSchemeID.FLEXIBLE:
            continue

        if not regulation.allow_offsetting:
            continue

        profile = regulation.profile

        remedial_cost = profile.remedial_cost
        flexibility_cost = profile.get_flexibility_cost()

        fig, ax = single_panel()

        ax.plot(dateline, remedial_cost, label='Remedial cost',
                color=CENTER_COLORS_RED[3], lw=2.)
        ax.plot(dateline, flexibility_cost, label='Flexibility cost (shadow price)',
                color=CENTER_COLORS_GREEN[3], lw=2.)

        if offsetting_cost_value is not None:
            if np.isscalar(offsetting_cost_value):
                ax.axhline(y=offsetting_cost_value, label='Offsetting cost',
                           color=CENTER_COLORS_BLUE[4], lw=2., ls='--')
            else:
                ax.plot(dateline, np.broadcast_to(offsetting_cost_value, dateline.shape),
                        label='Offsetting cost', color=CENTER_COLORS_BLUE[4], lw=2., ls='--')

        legend = ax.legend(**LEGEND_OPTIONS)

        ax.set_ylabel('Cost [USD/tCO$_2$-eq.]')
        ax.set_ylim([0., None])

        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend, y_lim=(None, None))

        save_figure(fig, directory, 'regulation_offsetting_cost_{}.png'.format(regulation_name))
