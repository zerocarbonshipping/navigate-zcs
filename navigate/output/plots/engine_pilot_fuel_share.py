# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)
from navigate.output.plots._labels import (
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    FUEL_TYPE_ORDER,
)


def _select_fuel_types(vessels):
    """
    Primary fuel types of vessels with a dual-fuel converter, in FUEL_TYPE_ORDER.

    get_pilot_fuel_share() keys its data by vessel.primary_fuel_type (every fuel
    a vessel bunkers is recorded under that single type, see
    navigate.bunker.transfer.bunker.transfer_bunker), not by any converter's own
    main fuel type, so the panel selection must use the same key.
    """
    vessel_types = {
        vessel.primary_fuel_type
        for vessel in vessels.values()
        if any(
            converter.is_dual_fuel()
            for converter in vessel.power_system.get_converters()
        )
    }
    return [fuel_type for fuel_type in FUEL_TYPE_ORDER if fuel_type in vessel_types]


def plot_engine_pilot_fuel_share(manager, directory):
    """Plot pilot fuel share per primary fuel type with a dual-fuel vessel."""
    dateline = manager.dateline
    vessels = manager.nodes.vessels

    relevant_fuel_types = _select_fuel_types(vessels)

    if not relevant_fuel_types:
        return

    fleet_pilot_fuel_share = manager.profile.get_pilot_fuel_share()
    pilot_fuel_share = {
        fuel_type: np.where(
            fleet_pilot_fuel_share[fuel_type] > 0.0,
            fleet_pilot_fuel_share[fuel_type],
            np.nan,
        )
        for fuel_type in relevant_fuel_types
    }

    # find minimum pilot fuel. Assuming it is constant and similar for all
    # converters. Too simplistic.
    minimum_share = dict.fromkeys(pilot_fuel_share, 0.0)

    for vessel in vessels.values():
        fuel_type = vessel.primary_fuel_type

        if fuel_type not in relevant_fuel_types:
            continue

        for converter in vessel.power_system.get_converters():
            if converter.is_dual_fuel():
                # assume share is constant
                min_share = converter.minimum_pilot_fuel.get()
                minimum_share[fuel_type] = max(minimum_share[fuel_type], min_share)

    fig, axes = subplot_grid(len(pilot_fuel_share))

    for ax, fuel_type in zip(axes, relevant_fuel_types, strict=False):
        share = pilot_fuel_share[fuel_type] * 100.0
        minimum = np.full_like(
            dateline, minimum_share[fuel_type] * 100.0, dtype=np.float64
        )

        ax.plot(
            dateline,
            share,
            color=FUEL_TYPE_COLOR[fuel_type],
            label="Actual share",
            lw=2.5,
        )
        ax.plot(dateline, minimum, color="k", ls="--", label="Minimum share", lw=1.5)

        ax.set_ylabel("Pilot fuel share [%]")
        ax.set_title(f"{FUEL_TYPE_LABEL[fuel_type]} vessels")
        legend = ax.legend()
        format_axes(ax, len(pilot_fuel_share), dateline, legend)

    for ax in axes:
        ax.set_ylim([0.0, 100.0])

    trim_axes(axes, len(pilot_fuel_share))

    save_figure(fig, directory, "engine_pilot_fuel_share.png")
