# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the cumulative vessel fuel conversions per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._labels import (
    FLEET_LABEL,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_ORDER,
    extract_label,
)
from navigate.output.plots._layout import trim_axes
from navigate.util import TOLERANCE, dates_to_years, sum_by_first_key, sum_by_second_key

if TYPE_CHECKING:
    from matplotlib.typing import ColorType

    from navigate.core.nodes.vessel import Vessel
    from navigate.core.simulation_results import SimulationResults
    from navigate.util.types_ import FloatArray


def _vessel_series_by_fuel_type(
    series: dict[str, FloatArray], vessel_map: dict[str, Vessel]
) -> tuple[list[FloatArray], list[ColorType]]:
    """Flat (values, colors) per vessel, in fuel-type order, near-zero dropped."""
    order = {fuel_type: i for i, fuel_type in enumerate(FUEL_TYPE_ORDER)}

    names = [
        name
        for name, values in series.items()
        if not np.all(np.abs(values) < TOLERANCE)
    ]
    names.sort(key=lambda name: order[vessel_map[name].primary_fuel_type])

    return (
        [series[name] for name in names],
        [FUEL_TYPE_COLOR[vessel_map[name].primary_fuel_type] for name in names],
    )


def plot_fleet_conversions_cumulative(
    results: SimulationResults, directory: str
) -> None:
    """Plot the cumulative number of vessels converted from and to each fuel type."""
    dateline = results.dateline
    fleets = results.nodes.fleets

    fuel_conversions = {
        fleet_name: fleet.profile.get_fuel_conversions()
        for fleet_name, fleet in fleets.items()
        if fleet.can_fuel_convert()
    }

    if not fuel_conversions:
        return

    fig, axes = subplot_grid(len(fuel_conversions))

    for ax, (fleet_name, conversions) in zip(
        axes, fuel_conversions.items(), strict=False
    ):
        vessel_map = {vessel.name: vessel for vessel in fleets[fleet_name].vessels}

        conversions_from = {
            key: -conversion
            for key, conversion in sum_by_first_key(conversions).items()
        }
        conversions_to = sum_by_second_key(conversions)

        values_from, colors_from = _vessel_series_by_fuel_type(
            conversions_from, vessel_map
        )
        values_to, colors_to = _vessel_series_by_fuel_type(conversions_to, vessel_map)

        time_steps = np.diff(dates_to_years(dateline))
        values_from = [np.cumsum(value[1:] * time_steps) for value in values_from]
        values_to = [np.cumsum(value[1:] * time_steps) for value in values_to]

        plot_stack_with_lines(ax, dateline[1:], values_from, [], colors_from)
        plot_stack_with_lines(ax, dateline[1:], values_to, [], colors_to)

        ax.plot([dateline[1], dateline[-1]], [0.0, 0.0], c="k", lw=2)

        ax.set_ylabel("Number of vessels")
        ax.set_title(extract_label(fleets[fleet_name], FLEET_LABEL))

        format_axes(ax, len(fuel_conversions), dateline[1:], y_lim=(None, None))

    trim_axes(axes, len(fuel_conversions))

    save_figure(fig, directory, "fleet_conversions_cumulative.png")
