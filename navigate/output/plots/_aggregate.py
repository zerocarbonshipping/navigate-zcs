# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Domain data-shaping for stacked plots.

Merges per-vessel and per-fuel model results into the ordered values, labels
and colors the plot modules stack, applying the canonical fuel-type ordering
and dropping negligible contributions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import generate_color_dict
from navigate.output.plots._labels import (
    FLEET_LABEL,
    FUEL_COLOR,
    FUEL_LABEL,
    FUEL_ORDER,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    FUEL_TYPE_ORDER,
    default_label,
    extract_label,
)
from navigate.util import (
    TOLERANCE,
    YEAR,
    dates_to_days,
    dates_to_years,
)

if TYPE_CHECKING:
    from matplotlib.typing import ColorType

    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.fuel import Fuel
    from navigate.util.types_ import DateArray, FloatArray


def merge_fuels_for_plot(
    dateline: DateArray, fuels: dict[str, Fuel], fuel_demand: dict[str, FloatArray]
) -> tuple[list[FloatArray], list[str], list[ColorType]]:
    fuels = {
        fuel_name: fuel for fuel_name, fuel in fuels.items() if fuel_name in fuel_demand
    }

    colors = generate_color_dict(fuels, FUEL_COLOR)
    labels = {name: default_label(name, FUEL_LABEL) for name in fuels}

    timeline = (dateline - dateline[0]).astype(np.float64)
    demand = {
        name: np.zeros_like(timeline, dtype=np.float64) + fuel_demand[name]
        for name in fuels
    }

    remove_below_threshold(demand, TOLERANCE)

    # canonical order first, then any remaining fuels not listed in FUEL_ORDER
    ordered_names = [name for name in FUEL_ORDER if name in demand]
    for name in fuels:
        if name not in ordered_names and name in demand:
            ordered_names.append(name)

    ordered_values = [demand[name] for name in ordered_names]
    ordered_labels = [labels[name] for name in ordered_names]
    ordered_colors = [colors[name] for name in ordered_names]

    return ordered_values, ordered_labels, ordered_colors


def merge_fleet_evolution(
    dateline: DateArray, fleet: Fleet
) -> tuple[list[FloatArray], list[str], list[ColorType], str]:
    return _merge_by_fuel_type(
        dateline,
        fleet,
        fleet.profile.get_existing_vessels(),
        threshold=1.0,
        normalize=False,
    )


def merge_fleet_scrap(
    dateline: DateArray, fleet: Fleet
) -> tuple[list[FloatArray], list[str], list[ColorType], str]:
    """Stack the fleet's yearly scrapped vessels by fuel type, as negative values."""
    return _merge_by_fuel_type(
        dateline,
        fleet,
        {name: -scrapped for name, scrapped in fleet.profile.get_scrap().items()},
        threshold=TOLERANCE,
        normalize=True,
    )


def merge_fleet_newbuilds(
    dateline: DateArray, fleet: Fleet
) -> tuple[list[FloatArray], list[str], list[ColorType], str]:
    """Stack the fleet's yearly newbuild vessels by fuel type."""
    return _merge_by_fuel_type(
        dateline,
        fleet,
        fleet.profile.get_newbuilds(),
        threshold=TOLERANCE,
        normalize=True,
    )


def _make_fuel_type_zeros(dateline: DateArray) -> dict[FuelTypeID, FloatArray]:
    """Create a dict of zero arrays keyed by FuelTypeID in standard plotting order."""
    return {
        fuel_type: np.zeros_like(dateline, dtype=np.float64)
        for fuel_type in FUEL_TYPE_ORDER
    }


def unpack_fuel_type_series(
    values: dict[FuelTypeID, FloatArray],
) -> tuple[list[FloatArray], list[str], list[ColorType]]:
    """Split {FuelTypeID: array} dict into parallel (values, labels, colors) lists."""
    return (
        list(values.values()),
        [FUEL_TYPE_LABEL[fuel_type] for fuel_type in values],
        [FUEL_TYPE_COLOR[fuel_type] for fuel_type in values],
    )


def _merge_by_fuel_type(
    dateline: DateArray,
    fleet: Fleet,
    series: dict[str, FloatArray],
    threshold: float,
    normalize: bool,
) -> tuple[list[FloatArray], list[str], list[ColorType], str]:
    """
    Accumulate the per-vessel series of a fleet into a fuel-type-keyed stack.

    Flows (newbuilds / scrap) are normalized to a per-year rate; stocks
    (existing vessels) pass normalize=False. Negligible fuel types are dropped
    and the result is the (values, labels, colors, title) tuple the plot
    modules stack.
    """
    values = _make_fuel_type_zeros(dateline)

    for vessel in fleet.vessels:
        values[vessel.primary_fuel_type] += series[vessel.name]

    # normalize the owned accumulators: the series are profile storage and
    # must not be mutated
    if normalize:
        time_steps = np.diff(dates_to_days(dateline)) / YEAR
        for value in values.values():
            value[1:] /= time_steps

    remove_below_threshold(values, threshold)

    actual_values, actual_labels, actual_colors = unpack_fuel_type_series(values)
    title = extract_label(fleet, FLEET_LABEL)

    return actual_values, actual_labels, actual_colors, title


def merge_fuel_costs(
    fuel_costs: dict[str, FloatArray], fuels: dict[str, Fuel]
) -> tuple[list[list[FloatArray]], list[list[ColorType]], list[str]]:
    """
    Group the fuel costs into per-fuel-type subplot lists.

    Returns parallel (values, colors, titles) lists -- one entry per fuel type that
    has data -- in canonical FUEL_TYPE_ORDER. Near-zero series are skipped and empty
    fuel-type groups are dropped.
    """
    fuel_colors = generate_color_dict(fuels, FUEL_COLOR)

    index_of = {fuel_type: i for i, fuel_type in enumerate(FUEL_TYPE_ORDER)}
    values: list[list[FloatArray]] = [[] for _ in FUEL_TYPE_ORDER]
    colors: list[list[ColorType]] = [[] for _ in FUEL_TYPE_ORDER]

    for name, result in fuel_costs.items():
        if np.all(np.abs(result) < TOLERANCE):
            continue

        i = index_of[fuels[name].fuel_type]
        values[i].append(result)
        colors[i].append(fuel_colors[name])

    titles = [FUEL_TYPE_LABEL[fuel_type] for fuel_type in FUEL_TYPE_ORDER]

    keep = [i for i, group in enumerate(values) if group]

    return (
        [values[i] for i in keep],
        [colors[i] for i in keep],
        [titles[i] for i in keep],
    )


def remove_below_threshold[K](values: dict[K, FloatArray], threshold: float) -> None:
    del_keys = []

    for key, value in values.items():
        if np.sum(np.abs(value)) < threshold:
            del_keys.append(key)

    for key in del_keys:
        del values[key]


def to_cumulative(dateline: DateArray, value: FloatArray) -> FloatArray:
    timeline = dates_to_years(dateline)
    # the first time step has no predecessor; assume it spans 1 year
    time_step = np.insert(np.diff(timeline), 0, 1.0)

    return np.cumsum(value * time_step)
