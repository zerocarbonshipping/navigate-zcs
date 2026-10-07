# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Pilot fuel share, one panel per primary fuel type with a dual-fuel vessel."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    FUEL_TYPE_ORDER,
)
from navigate.output.plots._layout import trim_axes

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.simulation_results import SimulationResults


def _select_fuel_types(vessels: dict[str, Vessel]) -> list[FuelTypeID]:
    """
    Primary fuel types of vessels with a matching dual-fuel converter.

    In FUEL_TYPE_ORDER. get_pilot_fuel_share() keys its data by
    vessel.primary_fuel_type (every fuel a vessel bunkers is recorded under
    that single type, see navigate.simulation.bunker.transfer.bunker.transfer_bunker). A
    vessel counts when one of its own converters is dual-fuel and lists the
    vessel's primary type among its main fuel types, keeping the resulting
    share and its minimum comparable.
    """
    vessel_types = {
        vessel.primary_fuel_type
        for vessel in vessels.values()
        if any(
            converter.is_dual_fuel()
            and vessel.primary_fuel_type in converter.main_fuel_types
            for converter in vessel.power_system.get_converters()
        )
    }
    return [fuel_type for fuel_type in FUEL_TYPE_ORDER if fuel_type in vessel_types]


def _minimum_pilot_share(
    vessels: dict[str, Vessel], fuel_types: list[FuelTypeID]
) -> dict[FuelTypeID, float]:
    """
    Per fuel type, the largest MinimumPilotFuel among matching converters.

    Assumes it is constant and similar for all converters. Too simplistic.
    For each vessel whose primary type is in fuel_types, its own converters
    that are dual-fuel and list that primary type among their main fuel types
    contribute their MinimumPilotFuel; the maximum is kept per type.
    """
    minimum_share = dict.fromkeys(fuel_types, 0.0)

    for vessel in vessels.values():
        fuel_type = vessel.primary_fuel_type

        if fuel_type not in minimum_share:
            continue

        for converter in vessel.power_system.get_converters():
            if converter.is_dual_fuel() and fuel_type in converter.main_fuel_types:
                converter_minimum = converter.minimum_pilot_fuel.get()
                minimum_share[fuel_type] = max(
                    minimum_share[fuel_type], converter_minimum
                )

    return minimum_share


def plot_engine_pilot_fuel_share(results: SimulationResults, directory: Path) -> None:
    """Plot pilot fuel share per primary fuel type with a matching dual-fuel vessel."""
    dateline = results.dateline
    vessels = results.nodes.vessels

    relevant_fuel_types = _select_fuel_types(vessels)

    if not relevant_fuel_types:
        return

    fleet_pilot_fuel_share = results.profile.get_pilot_fuel_share()
    pilot_fuel_share = {
        fuel_type: np.where(
            fleet_pilot_fuel_share[fuel_type] > 0.0,
            fleet_pilot_fuel_share[fuel_type],
            np.nan,
        )
        for fuel_type in relevant_fuel_types
    }

    minimum_share = _minimum_pilot_share(vessels, relevant_fuel_types)

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
        ax.set_ylim(0.0, 100.0)

    trim_axes(axes, len(pilot_fuel_share))

    save_figure(fig, directory, "engine_pilot_fuel_share.png")
