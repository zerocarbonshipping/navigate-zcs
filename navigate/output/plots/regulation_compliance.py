# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the compliance against the threshold, one figure per regulation."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
from navigate.output.plots._layout import (
    get_font_sizes,
    set_font_sizes,
    trim_axes,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import find_best_metric_prefix

if TYPE_CHECKING:
    from matplotlib.artist import Artist

    from navigate.output.plot_data import PlotData


def plot_regulation_compliance(plot_data: PlotData, directory: str) -> None:
    """Plot the compliance against the threshold, one figure per regulation."""
    dateline = plot_data.dateline
    regulations = plot_data.nodes.regulations

    for regulation_name, regulation in regulations.items():
        scheme = regulation.scheme
        measure = regulation.measure
        profile = regulation.profile
        has_threshold_adjustment = regulation.allow_threshold_adjustment

        if scheme == RegulationSchemeID.INDIVIDUAL:
            compliance = profile.get_vessel_compliance()
            thresholds = profile.get_vessel_threshold()

            if has_threshold_adjustment:
                adjusted = profile.get_adjusted_vessel_threshold()
                adjusted = {
                    key: value
                    for key, value in adjusted.items()
                    if key in thresholds and np.any(np.isfinite(value))
                }
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

            adjusted = {}
            if has_threshold_adjustment:
                shared_adjusted = profile.get_adjusted_shared_threshold()
                if np.any(np.isfinite(shared_adjusted)):
                    adjusted = {regulation_name: shared_adjusted}

        # a threshold that is never finite does not apply
        relevant_names = [
            name for name, value in thresholds.items() if np.any(np.isfinite(value))
        ]
        thresholds = {
            name: value for name, value in thresholds.items() if name in relevant_names
        }
        compliance = {
            name: value for name, value in compliance.items() if name in relevant_names
        }

        threshold_count = len(thresholds)

        if threshold_count == 0:
            continue

        fig, axes = subplot_grid(threshold_count, sharex=True)

        for ax, (name, threshold) in zip(axes, thresholds.items(), strict=False):
            if name not in compliance:
                continue

            measured = compliance[name]

            # an adjusted threshold, where set, decides what counts as compliant
            effective_threshold = adjusted.get(name, threshold)

            compliant = np.minimum(measured, effective_threshold)
            non_compliant = np.maximum(measured - effective_threshold, 0.0)

            if (
                (scheme == RegulationSchemeID.FLEXIBLE)
                and (
                    measure
                    in (
                        RegulationMeasureID.TRANSPORT,
                        RegulationMeasureID.TRANSPORT_NOMINAL,
                    )
                )
            ) or measure == RegulationMeasureID.ABSOLUTE:
                finite_measured = measured[np.isfinite(measured)]
                finite_threshold = threshold[np.isfinite(threshold)]

                max_measured = np.nan
                if finite_measured.size:
                    max_measured = np.max(finite_measured)

                max_threshold = np.nan
                if finite_threshold.size:
                    max_threshold = np.max(finite_threshold)

                divisor, prefix = find_best_metric_prefix(
                    np.maximum(max_measured, max_threshold)
                )
                compliant /= divisor
                non_compliant /= divisor
                threshold = threshold / divisor
                if name in adjusted:
                    effective_threshold = effective_threshold / divisor
                unit = f"{prefix}ton/year"

                ax.set_ylabel(f"Absolute [{unit}]")

            elif measure == RegulationMeasureID.INTENSITY:
                ax.set_ylabel("Intensity [kg/GJ]")

            elif measure == RegulationMeasureID.TRANSPORT:
                ax.set_ylabel("Transport [g/cargo-mile]")

            elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:
                ax.set_ylabel("Transport [g/nominal cargo-mile]")

            values = [compliant]
            labels = ["Compliant"]
            colors = [CENTER_COLORS_GREEN[3]]

            if np.any(non_compliant > 0.0):
                values.append(non_compliant)
                labels.append("Non-compliant")
                colors.append(CENTER_COLORS_RED[3])

            handles: list[Artist] = []

            stack = plot_stack_with_lines(
                ax, dateline, values, labels, colors, alpha=0.5
            )
            handles.extend(stack)

            # an adjusted threshold is the primary line, over the original one
            if name in adjusted:
                line = ax.plot(
                    dateline,
                    effective_threshold,
                    color="k",
                    ls=(0, (3, 3)),
                    label="Adjusted Threshold",
                    lw=2,
                )
                handles.extend(line)
                line_original = ax.plot(
                    dateline,
                    threshold,
                    color="grey",
                    ls=(0, (3, 3)),
                    label="Original Threshold",
                    lw=1.5,
                    alpha=0.7,
                )
                handles.extend(line_original)
                legend_labels = [*labels, "Adjusted Threshold", "Original Threshold"]
            else:
                line = ax.plot(
                    dateline,
                    threshold,
                    color="k",
                    ls=(0, (3, 3)),
                    label="Threshold",
                    lw=2,
                )
                handles.extend(line)
                legend_labels = [*labels, "Threshold"]

            ax.set_xlim(dateline[0], dateline[-1])

            if len(thresholds) > 1:
                ax.set_title(name)

            ax.grid(True, lw=0.3, alpha=0.5)

            if threshold_count <= 9:
                ax.legend(handles, legend_labels, **LEGEND_OPTIONS)

            set_font_sizes(ax, *get_font_sizes(len(axes)))

        trim_axes(axes, len(thresholds))

        save_figure(fig, directory, f"regulation_compliance_{regulation_name}.png")
