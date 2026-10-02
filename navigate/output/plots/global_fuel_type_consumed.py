# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Fuel consumed over time, stacked by fuel type a deck uses."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import get_fuels_per_fuel_type
from navigate.output.plots._aggregate import unpack_fuel_type_series
from navigate.output.plots._colors import SHORE_POWER_COLOR
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._labels import FUEL_TYPE_ORDER
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_energy

if TYPE_CHECKING:
    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.fuel import Fuel
    from navigate.output.plot_data import PlotData


def _select_fuel_types(
    fuel_type_to_fuels: dict[FuelTypeID, list[Fuel]],
) -> list[FuelTypeID]:
    """
    Fuel types with a declared Fuel, in FUEL_TYPE_ORDER.

    get_fuel_type_energy() is built from bunkered fuel mass, which is keyed only
    by declared Fuel names, so it is exactly zero for a type no Fuel declares.
    """
    return [fuel_type for fuel_type in FUEL_TYPE_ORDER if fuel_type_to_fuels[fuel_type]]


def plot_global_fuel_type_consumed(plot_data: PlotData, directory: str) -> None:
    """Plot fuel consumed over time, stacked by fuel type a deck uses."""
    dateline = plot_data.dateline
    fuels = plot_data.nodes.fuels

    fuel_type_consumed = plot_data.profile.get_fuel_type_energy()
    fuel_type_to_fuels = get_fuels_per_fuel_type(fuels)
    fuel_type_consumed = {
        fuel_type: fuel_type_consumed[fuel_type]
        for fuel_type in _select_fuel_types(fuel_type_to_fuels)
    }

    if not fuel_type_consumed:
        return

    fig, ax = single_panel()

    shore_power = plot_data.profile.get_shore_power_energy()

    divisor, unit = get_best_unit_energy(
        np.amax(sum(list(fuel_type_consumed.values())) + shore_power), unit_order=9
    )
    fuel_type_consumed = {
        fuel_type: demand / divisor for fuel_type, demand in fuel_type_consumed.items()
    }
    shore_power_scaled = shore_power / divisor

    values, labels, colors = unpack_fuel_type_series(fuel_type_consumed)

    if np.any(shore_power_scaled > 0.0):
        values.append(shore_power_scaled)
        labels.append("Shore Power")
        colors.append(SHORE_POWER_COLOR)

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel(f"Fuel consumed [{unit}]")
    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, "global_fuel_type_consumed.png")
