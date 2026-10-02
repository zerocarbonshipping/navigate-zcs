# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the investment signals of each vessel per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FLEET_LABEL,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    extract_label,
)
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.profiles.vessel_profile import VesselProfile
    from navigate.output.plot_data import PlotData
    from navigate.util.types_ import FloatArray


def plot_fleet_investment_signal_technology_per_vessel(
    plot_data: PlotData, directory: str
) -> None:
    """Plot the technology investment signal of each vessel per fleet."""
    _plot_investment_signal_per_vessel(
        plot_data,
        directory,
        lambda profile: profile.get_investment_signal_technology(),
        "fleet_investment_signal_technology_per_vessel.png",
    )


def plot_fleet_investment_signal_speed_per_vessel(
    plot_data: PlotData, directory: str
) -> None:
    """Plot the speed investment signal of each vessel per fleet."""
    _plot_investment_signal_per_vessel(
        plot_data,
        directory,
        lambda profile: profile.get_investment_signal_speed(),
        "fleet_investment_signal_speed_per_vessel.png",
    )


def _plot_investment_signal_per_vessel(
    plot_data: PlotData,
    directory: str,
    signal_getter: Callable[[VesselProfile], FloatArray],
    filename: str,
) -> None:
    dateline = plot_data.dateline
    fleets = plot_data.nodes.fleets
    relevant_fleets = {
        fleet_name: fleet for fleet_name, fleet in fleets.items() if fleet.vessels
    }

    if not relevant_fleets:
        return

    fig, axes = subplot_grid(len(relevant_fleets))

    for ax, fleet in zip(axes, relevant_fleets.values(), strict=False):
        # each vessel carries its energy-weighted investment signal
        signals = []
        for vessel in fleet.vessels:
            signal = signal_getter(vessel.profile)
            label = FUEL_TYPE_LABEL[vessel.primary_fuel_type]
            color = FUEL_TYPE_COLOR[vessel.primary_fuel_type]

            ax.plot(dateline, signal, label=label, color=color, lw=2.0)
            signals.append(signal)

        ax.set_ylabel("Investment signal [USD/GJ]")
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        legend = ax.legend()

        # only floor the y-axis at zero when no vessel ever sees a negative signal
        y_lim = (0.0, None) if _signals_all_non_negative(signals) else None
        format_axes(ax, len(relevant_fleets), dateline, legend, y_lim=y_lim)

    trim_axes(axes, len(relevant_fleets))

    save_figure(fig, directory, filename)


def _signals_all_non_negative(signals: list[FloatArray]) -> bool:
    """Return True when no vessel signal dips below zero, ignoring NaN time-steps."""
    return all(
        np.nanmin(signal) >= 0.0 for signal in signals if np.any(np.isfinite(signal))
    )
