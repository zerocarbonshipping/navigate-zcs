# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.output.plots._colors import CENTER_COLORS_GREEN
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.output.plots._labels import FUEL_TYPE_COLOR
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import find_best_metric_prefix


def plot_regulation_flexibility(manager, directory):

    dateline = manager.get_dateline()
    regulations = manager.nodes.regulations
    vessels = manager.nodes.vessels

    for regulation_name, regulation in regulations.items():

        if not regulation.measure == RegulationMeasureID.INTENSITY:
            continue

        if not regulation.scheme == RegulationSchemeID.FLEXIBLE:
            continue

        shared_threshold = regulation.profile.get_shared_threshold()
        shared_compliance = regulation.profile.get_shared_compliance()
        vessel_compliance = regulation.profile.get_vessel_compliance()

        vessel_compliance = {v: c for v, c in vessel_compliance.items() if regulation.vessel_is_policed(v)}

        fig, ax = single_panel()

        measure = regulation.measure
        if measure == RegulationMeasureID.ABSOLUTE:

            divisor, prefix = find_best_metric_prefix(
                np.amax(np.maximum(shared_threshold, shared_compliance)))
            unit = '{}ton/year'.format(prefix)

        else:
            unit = ''

        # plot shared threshold and compliance
        patches = []
        line = ax.plot(dateline, shared_threshold, label='Threshold', color='k', lw=2.)
        patches.extend(line)
        line = ax.plot(dateline, shared_compliance, label='Compliance', color=CENTER_COLORS_GREEN[3], lw=2.)
        patches.extend(line)

        for v, compliance in vessel_compliance.items():
            color = FUEL_TYPE_COLOR[vessels[v].fuel_type]
            line = ax.plot(dateline, compliance, color=color, alpha=0.5, lw=1.)

        patches.extend(line)
        labels = ['Threshold', 'Compliance', 'Ind. compliance']
        legend = ax.legend(patches, labels, **LEGEND_OPTIONS)

        if measure == RegulationMeasureID.ABSOLUTE:
            ax.set_ylabel('Absolute [{}]'.format(unit))

        elif measure == RegulationMeasureID.INTENSITY:
            ax.set_ylabel('Intensity [kg/GJ]')

        elif measure == RegulationMeasureID.TRANSPORT:
            ax.set_ylabel('Transport [g/cargo-mile]')

        elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:
            ax.set_ylabel('Transport [g/nominal cargo-mile]')

        ax.set_ylim([0., None])

        ax.grid(True, lw=0.3, alpha=0.5)
        format_axes(ax, 1, dateline, legend)

        save_figure(fig, directory, 'regulation_flexibility_{}.png'.format(regulation_name))
