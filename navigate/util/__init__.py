# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Domain-agnostic helpers.

Collections, dates, naming, numerics, timings and units; the type aliases are
imported from ``navigate.util.types_`` directly.
"""

from __future__ import annotations

from navigate.util.collections import (
    add_dicts,
    index_map,
    is_single_dict,
    is_tuple_dict,
    is_unique,
    list_intersection,
    slice_array,
    slice_dict,
    slice_dict_list,
    slice_list,
    sum_by_first_key,
    sum_by_second_key,
    sum_nonempty_values,
    sum_per_key,
    sum_values,
    unique_list,
)
from navigate.util.dates import (
    YEAR,
    dates_to_days,
    dates_to_years,
    is_date_array,
    timedelta_to_days,
)
from navigate.util.naming import (
    attribute_to_instance_name,
    attribute_to_setter,
    key_name,
    matching_keys,
    name_contains_wildcards,
    retrieve_keys,
    setter_to_attribute,
)
from navigate.util.numeric import (
    ROUND_OFF,
    TOLERANCE,
    calculate_compound_growth,
    calculate_smoothing_alpha,
    calculate_step_inertia,
    divide_nonzero,
    find_nearest_index,
    find_nearest_indices,
    interpolate_yearly_flow,
    is_nondecreasing,
    is_strictly_increasing,
    step_lengths,
    update_belief_path,
)
from navigate.util.timings import Timings, timed
from navigate.util.units import (
    HOUR_TO_DAY,
    MWH_TO_GJ,
    TON_PER_GJ_TO_GRAM_PER_MJ,
    TON_TO_GRAM,
    TON_TO_KG,
    energy_to_power,
    power_to_energy,
)
