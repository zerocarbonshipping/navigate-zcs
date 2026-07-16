# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationSchemeID
from navigate.illustrations.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)
from navigate.illustrations.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.illustrations.plots._style import (
    LEGEND_OPTIONS,
)
from navigate.illustrations.plots._units import find_best_metric_prefix


def plot_regulation_offsetting_units(manager, directory):

    dateline = manager.get_dateline()
    regulations = manager.nodes.regulations

    for regulation_name, regulation in regulations.items():

        if not regulation.scheme == RegulationSchemeID.FLEXIBLE:
            continue

        if not regulation.allow_offsetting:
            continue

        profile = regulation.profile

        offsetting_units = profile.get_offsetting_units()
        flexibility_units = profile.get_flexibility_units()
        remedial_units = profile.get_remedial_units()

        total = offsetting_units + flexibility_units + remedial_units
        if not np.any(total > 0.):
            continue

        divisor, prefix = find_best_metric_prefix(np.amax(total))

        fig, ax = single_panel()

        values = []
        labels = []
        colors = []

        if np.any(offsetting_units > 0.):
            values.append(offsetting_units / divisor)
            labels.append('Offsetting')
            colors.append(CENTER_COLORS_BLUE[3])

        if np.any(flexibility_units > 0.):
            values.append(flexibility_units / divisor)
            labels.append('Flexibility')
            colors.append(CENTER_COLORS_YELLOW[3])

        if np.any(remedial_units > 0.):
            values.append(remedial_units / divisor)
            labels.append('Remedial')
            colors.append(CENTER_COLORS_RED[3])

        stack = plot_stack_with_lines(ax, dateline, values, labels, colors, alpha=0.5)

        legend = ax.legend(stack, labels, **LEGEND_OPTIONS)
        ax.set_ylabel('Non-compliance units [{}tCO$_2$-eq/year]'.format(prefix))
        ax.set_ylim([0., None])
        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend)

        save_figure(fig, directory, 'regulation_offsetting_units_{}.png'.format(regulation_name))
