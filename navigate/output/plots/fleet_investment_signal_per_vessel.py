# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import trim_axes
from navigate.output.plots._labels import (
    FLEET_LABEL,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    extract_label,
)


def plot_fleet_investment_signal_technology_per_vessel(manager, directory):
    dateline = manager.get_dateline()
    _plot_investment_signal_per_vessel(dateline, manager, directory,
                                       lambda profile: profile.get_investment_signal_technology(),
                                       'fleet_investment_signal_technology_per_vessel.png')


def plot_fleet_investment_signal_speed_per_vessel(manager, directory):
    dateline = manager.get_dateline()
    _plot_investment_signal_per_vessel(dateline, manager, directory,
                                       lambda profile: profile.get_investment_signal_speed(),
                                       'fleet_investment_signal_speed_per_vessel.png')


def _plot_investment_signal_per_vessel(dateline, manager, directory, signal_getter, filename):

    fleets = manager.nodes.fleets
    relevant_fleets = {fleet_name: fleet for fleet_name, fleet in fleets.items() if fleet.get_vessels()}

    if not relevant_fleets:
        return

    fig, axes = subplot_grid(len(relevant_fleets))

    for ax, fleet in zip(axes, relevant_fleets.values()):

        # plot the energy-weighted investment signal per vessel
        signals = []
        for vessel in fleet.get_vessels():

            signal = signal_getter(vessel.profile)
            label = FUEL_TYPE_LABEL[vessel.fuel_type]
            color = FUEL_TYPE_COLOR[vessel.fuel_type]

            ax.plot(dateline, signal, label=label, color=color, lw=2.)
            signals.append(signal)

        ax.set_ylabel('Investment signal [USD/GJ]')
        ax.set_title(extract_label(fleet, FLEET_LABEL))
        leg = ax.legend()

        # only floor the y-axis at zero when no vessel ever sees a negative signal
        y_lim = (0., None) if _signals_all_non_negative(signals) else None
        format_axes(ax, len(relevant_fleets), dateline, legend=leg, y_lim=y_lim)

    trim_axes(axes, len(relevant_fleets))

    save_figure(fig, directory, filename)


def _signals_all_non_negative(signals):
    """True when no vessel signal dips below zero, ignoring NaN time-steps."""

    return all(np.nanmin(signal) >= 0. for signal in signals if np.any(np.isfinite(signal)))
