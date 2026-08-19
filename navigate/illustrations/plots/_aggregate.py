# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Domain data-shaping for stacked plots.

Merges per-vessel / per-plant / per-fuel model results into the ordered
(values, labels, colours, title) tuples the plot modules stack, applying the
canonical fuel-type ordering and dropping negligible contributions.
"""

import numpy as np

from navigate.core.misc import TOLERANCE, YEAR
from navigate.illustrations.plots._colors import generate_color_dict
from navigate.illustrations.plots._labels import (
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
    dates_to_days,
    dates_to_years,
)


def merge_fuels_for_plot(dateline, fuels, fuel_demand):

    # limit to fuels that actually have demand
    fuels = {fuel_name: fuel for fuel_name, fuel in fuels.items() if fuel_name in fuel_demand}

    colors = generate_color_dict(fuels, FUEL_COLOR)
    labels = {name: default_label(name, FUEL_LABEL) for name in fuels}

    timeline = (dateline - dateline[0]).astype(np.float64)
    demand = {name: np.zeros_like(timeline, dtype=np.float64) + fuel_demand[name] for name in fuels}

    # drop fuels with negligible demand
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


def merge_fleet_evolution(dateline, fleet):

    return _merge_by_fuel_type(
        dateline, fleet, FLEET_LABEL,
        items_fn=lambda f: f.get_vessels(),
        value_fn=lambda profile, vessel: profile.get_existing_vessels(vessel.get_name()),
        fuel_type_fn=lambda vessel: vessel.fuel_type,
        threshold=1.,
        normalize=False,
    )


def _make_fuel_type_zeros(dateline):
    """Create a dict of zero arrays keyed by FuelTypeID in standard plotting order."""
    return {ft: np.zeros_like(dateline, dtype=np.float64) for ft in FUEL_TYPE_ORDER}


def unpack_fuel_type_series(values):
    """Split a {FuelTypeID: array} dict into parallel (values, labels, colours) lists."""
    return (
        list(values.values()),
        [FUEL_TYPE_LABEL[ft] for ft in values],
        [FUEL_TYPE_COLOR[ft] for ft in values],
    )


def _merge_by_fuel_type(dateline, entity, label_dict, items_fn, value_fn, fuel_type_fn,
                        threshold, normalize=True):
    """Accumulate per-item series into a fuel-type-keyed stack.

    Shared by merge_fleet_evolution and merge_fleet_changes.
    Flows (newbuilds / scrap / decommissions) are normalized to a per-year rate; stocks
    (existing vessels) pass normalize=False. Negligible fuel types are dropped and the
    result is the (values, labels, colours, title) tuple the plot modules stack.
    """

    profile = entity.profile
    values = _make_fuel_type_zeros(dateline)

    for item in items_fn(entity):
        values[fuel_type_fn(item)] += value_fn(profile, item)

    # normalize the owned accumulators: value_fn results may be views of
    # profile storage and must not be mutated
    if normalize:
        time_steps = np.diff(dates_to_days(dateline)) / YEAR
        for value in values.values():
            value[1:] /= time_steps

    remove_below_threshold(values, threshold)

    actual_values, actual_labels, actual_colors = unpack_fuel_type_series(values)
    title = extract_label(entity, label_dict)

    return actual_values, actual_labels, actual_colors, title


def merge_fleet_changes(dateline, fleet, scrap=True):

    if scrap:
        value_fn = lambda profile, vessel: -profile.get_scrap(vessel.get_name())
    else:
        value_fn = lambda profile, vessel: profile.get_newbuilds(vessel.get_name())

    return _merge_by_fuel_type(
        dateline, fleet, FLEET_LABEL,
        items_fn=lambda f: f.get_vessels(),
        value_fn=value_fn,
        fuel_type_fn=lambda vessel: vessel.fuel_type,
        threshold=TOLERANCE,
    )


def group_series_by_fuel_type(series, fuel_type_of, color_of):
    """Group a {name: array} dict into per-fuel-type subplot lists.

    Returns parallel (values, colours, titles) lists -- one entry per fuel type that
    has data -- in canonical FUEL_TYPE_ORDER. Near-zero series are skipped and empty
    fuel-type groups are dropped.
    """

    index_of = {ft: i for i, ft in enumerate(FUEL_TYPE_ORDER)}
    values = [[] for _ in FUEL_TYPE_ORDER]
    colors = [[] for _ in FUEL_TYPE_ORDER]

    for name, result in series.items():

        if np.all(np.abs(result) < TOLERANCE):
            continue

        i = index_of.get(fuel_type_of(name))
        if i is not None:
            values[i].append(result)
            colors[i].append(color_of(name))

    titles = [FUEL_TYPE_LABEL[ft] for ft in FUEL_TYPE_ORDER]

    keep = [i for i, group in enumerate(values) if group]

    return [values[i] for i in keep], [colors[i] for i in keep], [titles[i] for i in keep]


def merge_fuel_costs(fuel_costs, fuels):

    colors = generate_color_dict(fuels, FUEL_COLOR)

    return group_series_by_fuel_type(
        fuel_costs,
        fuel_type_of=lambda name: fuels[name].fuel_type,
        color_of=lambda name: colors[name],
    )


def remove_below_threshold(values, threshold):
    del_keys = []

    for fuel_type, value in values.items():

        if np.sum(np.abs(value)) < threshold:
            del_keys.append(fuel_type)

    for key in del_keys:
        del values[key]


def to_cumulative(dateline, value):
    # translate to cumulative cost
    timeline = dates_to_years(dateline)
    time_step = np.insert(np.diff(timeline), 0, 1.)  # length of first time-step is undefined, assume 1 year.

    return np.cumsum(value * time_step)
