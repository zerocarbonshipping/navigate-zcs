# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Domain-agnostic helpers.

Collections, dates, naming, numerics, timings, types and units.
"""

from __future__ import annotations

from navigate.util.collections import (
    add_dicts,
    define_index_map,
    is_single_dict,
    is_tuple_dict,
    list_intersection,
    list_is_unique,
    slice_dict,
    slice_dict_list,
    slice_list,
    sum_by_first_key,
    sum_by_second_key,
    sum_dict_results,
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
    calculate_step_inertia,
    derive_smoothing_alpha,
    divide_nonzero,
    find_nearest,
    find_nearest_index,
    interpolate_yearly_flow,
    is_nondecreasing,
    is_strictly_increasing,
    step_lengths,
    update_belief_path,
)
from navigate.util.timings import Timings, timed
from navigate.util.types_ import (
    BoolArray,
    DateArray,
    FloatArray,
    FloatLike,
    Index,
    IntArray,
    TimedeltaArray,
)
from navigate.util.units import (
    DAY_TO_HOURS,
    GJ_TO_MJ,
    HOUR_TO_DAYS,
    MWD_TO_GJ,
    MWH_TO_GJ,
    TON_PER_GJ_TO_GRAM_PER_MJ,
    TON_TO_GRAM,
    TON_TO_KG,
)
