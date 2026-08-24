# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.output.plots._colors import (
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    get_font_sizes,
    set_font_sizes,
    trim_axes,
)
from navigate.output.plots._style import (
    LEGEND_OPTIONS,
)
from navigate.output.plots._units import find_best_metric_prefix


def plot_regulation_compliance(manager, directory):

    dateline = manager.get_dateline()
    regulations = manager.nodes.regulations

    for regulation_name, regulation in regulations.items():

        scheme = regulation.scheme
        measure = regulation.measure
        profile = regulation.profile
        has_threshold_adjustment = regulation.allow_threshold_adjustment

        if scheme == RegulationSchemeID.INDIVIDUAL:

            compliance = profile.get_vessel_compliance()
            thresholds = profile.get_vessel_threshold()

            # remove non-assigned vessels
            vessels = manager.nodes.vessels
            compliance = {key: value for key, value in compliance.items() if vessels[key].is_assigned_to_fleet()}
            thresholds = {key: value for key, value in thresholds.items() if vessels[key].is_assigned_to_fleet()}

            # retrieve adjusted thresholds for the compliance coloring
            if has_threshold_adjustment:
                adjusted = profile.get_adjusted_vessel_threshold()
                adjusted = {key: value for key, value in adjusted.items()
                            if key in thresholds and np.any(np.isfinite(value))}
            else:
                adjusted = {}

        else:

            if measure in (RegulationMeasureID.ABSOLUTE, RegulationMeasureID.INTENSITY):

                compliance = {regulation_name: profile.get_shared_compliance()}
                thresholds = {regulation_name: profile.get_shared_threshold()}

            else:

                # transport based regulations are not guaranteed to
                # share the same unit (TEU, tons, CEU, etc.) and
                # therefore they cannot be compared on an intensity basis
                compliance = {regulation_name: profile.get_shared_units()}
                thresholds = {regulation_name: profile.get_shared_allowance()}

            # retrieve the adjusted shared threshold directly
            adjusted = {}
            if has_threshold_adjustment:
                shared_adjusted = profile.get_adjusted_shared_threshold()
                if np.any(np.isfinite(shared_adjusted)):
                    adjusted = {regulation_name: shared_adjusted}

        if not thresholds:
            continue

        # screen out nans
        relevant_names = [name for name, value in thresholds.items() if np.any(np.isfinite(value))]
        thresholds = {name: value for name, value in thresholds.items() if name in relevant_names}
        compliance = {name: value for name, value in compliance.items() if name in relevant_names}

        n = len(thresholds)

        if n == 0:
            continue

        fig, axes = subplot_grid(n, sharex=True)

        for ax, (name, threshold) in zip(axes, thresholds.items()):

            if name not in compliance:
                continue

            measured = compliance[name]

            # use adjusted threshold for compliance coloring if available
            effective_threshold = adjusted[name] if name in adjusted else threshold

            # split the measured values into compliant and in breach
            compliant = np.minimum(measured, effective_threshold)
            non_compliant = np.maximum(measured - effective_threshold, 0.)

            if (((scheme == RegulationSchemeID.FLEXIBLE)
                 and (measure in (RegulationMeasureID.TRANSPORT, RegulationMeasureID.TRANSPORT_NOMINAL)))
                    or measure == RegulationMeasureID.ABSOLUTE):

                finite_measured = measured[np.isfinite(measured)]
                finite_threshold = threshold[np.isfinite(threshold)]

                max_measured = np.nan
                if finite_measured.size:
                    max_measured = np.max(finite_measured)

                max_threshold = np.nan
                if finite_threshold.size:
                    max_threshold = np.max(finite_threshold)

                divisor, prefix = find_best_metric_prefix(np.maximum(max_measured, max_threshold))
                compliant /= divisor
                non_compliant /= divisor
                threshold = threshold / divisor
                if name in adjusted:
                    effective_threshold = effective_threshold / divisor
                unit = '{}ton/year'.format(prefix)

                ax.set_ylabel('Absolute [{}]'.format(unit))

            elif measure == RegulationMeasureID.INTENSITY:

                ax.set_ylabel('Intensity [kg/GJ]')

            elif measure == RegulationMeasureID.TRANSPORT:

                ax.set_ylabel('Transport [g/cargo-mile]')

            elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:

                ax.set_ylabel('Transport [g/nominal cargo-mile]')

            values = [compliant]
            labels = ['Compliant']
            colors = [CENTER_COLORS_GREEN[3]]

            if np.any(non_compliant > 0.):
                values.append(non_compliant)
                labels.append('Non-compliant')
                colors.append(CENTER_COLORS_RED[3])

            patches = []

            stack = plot_stack_with_lines(ax, dateline, values, labels, colors, alpha=0.5)

            patches.extend(stack)

            # plot the adjusted threshold as the primary line if available
            if name in adjusted:
                line = ax.plot(dateline, effective_threshold, color='k', ls=(0, (3, 3)),
                               label='Adjusted Threshold', lw=2)
                patches.extend(line)
                # overlay the original threshold as a thinner grey dashed line
                line_orig = ax.plot(dateline, threshold, color='grey', ls=(0, (3, 3)),
                                    label='Original Threshold', lw=1.5, alpha=0.7)
                patches.extend(line_orig)
                leg_labels = [*labels, 'Adjusted Threshold', 'Original Threshold']
            else:
                line = ax.plot(dateline, threshold, color='k', ls=(0, (3, 3)), label='Threshold', lw=2)
                patches.extend(line)
                leg_labels = [*labels, 'Threshold']

            ax.set_xlim([dateline[0], dateline[-1]])
            # ax.set_ylim([0., None])

            if len(thresholds) > 1:
                ax.set_title(name)  # TODO: add back if multiple global regulations

            ax.grid(True, lw=0.3, alpha=0.5)

            if n <= 9:
                ax.legend(patches, leg_labels, **LEGEND_OPTIONS)

            set_font_sizes(ax, *get_font_sizes(len(axes)))

        trim_axes(axes, len(thresholds))

        save_figure(fig, directory, 'regulation_compliance_{}.png'.format(regulation_name))
