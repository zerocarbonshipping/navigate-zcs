# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationSchemeID
from navigate.output.plots._colors import CENTER_COLORS_GREEN
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.output.plots._units import find_best_metric_prefix


def plot_regulation_unit_trading(manager, directory):

    dateline = manager.dateline
    regulations = manager.nodes.regulations

    for regulation_name, regulation in regulations.items():

        if not regulation.scheme == RegulationSchemeID.FLEXIBLE:
            continue

        fig, ax = single_panel()

        non_compliance_units = regulation.profile.get_non_compliance_units()
        flexibility_units = regulation.profile.get_flexibility_units()
        remedial_units = regulation.profile.get_remedial_units()
        surplus_units = regulation.profile.get_surplus_units()

        divisor, prefix = find_best_metric_prefix(
            max(np.amax(non_compliance_units),
                np.amax(surplus_units),
                np.amax(flexibility_units),
                np.amax(remedial_units)),
            symbol=False)
        non_compliance_units /= divisor
        surplus_units /= divisor
        flexibility_units /= divisor
        remedial_units /= divisor

        unit = '{} units/year'.format(prefix)

        ax.plot(dateline, non_compliance_units, label='Non-compliance', color='k', lw=2.)
        ax.plot(dateline, surplus_units, label='Surplus', color=CENTER_COLORS_GREEN[3], lw=2.)

        legend = ax.legend()

        ax.set_ylabel(unit)

        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend, y_lim=(None, None))

        save_figure(fig, directory, 'regulation_unit_trading_{}.png'.format(regulation_name))
