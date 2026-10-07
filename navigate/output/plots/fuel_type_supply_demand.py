# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Fuel supply against demand, one panel per fuel type a deck uses."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import get_fuels_per_fuel_type
from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FUEL_COLOR,
    FUEL_LABEL,
    FUEL_TYPE_LABEL,
    FUEL_TYPE_ORDER,
    default_label,
)
from navigate.output.plots._layout import trim_axes
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_energy

if TYPE_CHECKING:
    from pathlib import Path

    from matplotlib.artist import Artist
    from matplotlib.typing import ColorType

    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.simulation_results import SimulationResults
    from navigate.util.types_ import FloatArray


def _select_fuel_types(
    fuel_type_to_fuels: dict[FuelTypeID, list[Fuel]],
    converters: dict[str, Converter],
) -> list[FuelTypeID]:
    """
    Fuel types with a declared Fuel or a converter using them, in FUEL_TYPE_ORDER.

    A converter can carry demand for a fuel type with no declared Fuel (fleet
    aggregation sums demand by MainFuelTypes/PilotFuelTypes alone), so a panel
    also appears for a type no Fuel declares but some converter does.
    """
    converter_fuel_types = {
        fuel_type
        for converter in converters.values()
        for fuel_type in converter.get_fuel_types()
    }
    return [
        fuel_type
        for fuel_type in FUEL_TYPE_ORDER
        if fuel_type_to_fuels[fuel_type] or fuel_type in converter_fuel_types
    ]


def plot_fuel_type_supply_demand(results: SimulationResults, directory: Path) -> None:
    """Plot fuel supply against demand for each fuel type a deck uses."""
    dateline = results.dateline
    ports = results.nodes.ports
    fuels = results.nodes.fuels
    converters = results.nodes.converters
    profile = results.profile

    fuel_type_to_fuels = get_fuels_per_fuel_type(fuels)
    fuel_types = _select_fuel_types(fuel_type_to_fuels, converters)

    if not fuel_types:
        return

    fuel_type_demand = profile.get_fuel_type_demand()
    production_type_energy = profile.get_production_type_energy()
    port_bunkering = [port.profile.get_bunker_energy() for port in ports.values()]

    # the series are kept until their overall maximum sets the shared unit
    all_values: dict[FuelTypeID, list[FloatArray]] = {}
    all_colors: dict[FuelTypeID, list[ColorType]] = {}
    all_labels: dict[FuelTypeID, list[str]] = {}
    all_demand: dict[FuelTypeID, FloatArray] = {}
    all_fuel_supply: dict[FuelTypeID, FloatArray] = {}

    maximum = 0.0

    for fuel_type in fuel_types:
        usable_fuels = fuel_type_to_fuels[fuel_type]
        fuel_spend: dict[str, FloatArray] = {}
        fuel_demand = fuel_type_demand[fuel_type]
        fuel_supply = production_type_energy[fuel_type]

        for bunkering in port_bunkering:
            for fuel in usable_fuels:
                if fuel.liquid_market or fuel.name not in bunkering:
                    continue

                # the sum owns its array so the in-place accumulation never
                # writes into a port's bunkering dict
                if fuel.name in fuel_spend:
                    fuel_spend[fuel.name] += bunkering[fuel.name]
                else:
                    fuel_spend[fuel.name] = bunkering[fuel.name].copy()

        values = list(fuel_spend.values())
        colors = list(generate_color_dict(fuel_spend, FUEL_COLOR).values())
        labels = [default_label(fuel_name, FUEL_LABEL) for fuel_name in fuel_spend]

        maximum = max(
            maximum,
            np.amax(fuel_demand),
            *(np.amax(value) for value in values),
            np.amax(fuel_supply),
        )

        all_values[fuel_type] = values
        all_colors[fuel_type] = colors
        all_labels[fuel_type] = labels
        all_demand[fuel_type] = fuel_demand
        all_fuel_supply[fuel_type] = fuel_supply

    if maximum <= 0.0:
        return

    divisor, unit = get_best_unit_energy(maximum, unit_order=9)

    fig, axes = subplot_grid(len(fuel_types))

    for ax, fuel_type in zip(axes, fuel_types, strict=False):
        values = [value / divisor for value in all_values[fuel_type]]
        colors = all_colors[fuel_type]
        labels = all_labels[fuel_type]

        fuel_demand = all_demand[fuel_type] / divisor
        fuel_supply = all_fuel_supply[fuel_type] / divisor

        handles: list[Artist] = []

        if values:
            stack = plot_stack_with_lines(
                ax, dateline, values, labels, colors, alpha=0.5
            )
            handles.extend(stack)

        line_demand = ax.plot(
            dateline, fuel_demand, label="Demand", ls=(0, (5, 3)), color="r", lw=2
        )
        handles.extend(line_demand)
        legend_labels = [*labels, "Demand"]

        line_supply = ax.plot(
            dateline, fuel_supply, label="Supply", ls=(0, (5, 3)), color="b", lw=2
        )
        handles.extend(line_supply)
        legend_labels.append("Supply")

        ax.set_ylabel(f"Fuel [{unit}]")
        ax.set_title(FUEL_TYPE_LABEL[fuel_type])
        legend = ax.legend(handles, legend_labels, **LEGEND_OPTIONS)
        format_axes(ax, len(fuel_types), dateline, legend)

    trim_axes(axes, len(fuel_types))

    save_figure(fig, directory, "fuel_type_supply_demand.png")
