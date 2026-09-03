# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.util.collections import (
    add_dicts,
    collapse_dict,
    collapse_tuple_dict,
    define_index_map,
    divide_dicts,
    extract_from_dict,
    extract_from_dict_list,
    extract_from_tuple_dict,
    is_single_dict,
    is_tuple_dict,
    list_intersection,
    list_is_unique,
    merge_dicts,
    multiply_dicts,
    slice_dict,
    slice_list,
    sum_dict_results,
    sum_tuple_dict_results,
    unique_list,
)
from navigate.util.dates import (
    DAY,
    MONTH,
    YEAR,
    dates_to_days,
    dates_to_years,
    decompose_dates,
    timedelta_to_days,
)
from navigate.util.naming import (
    attribute_to_setter,
    matching_keys,
    name_contains_wildcards,
    retrieve_keys,
    wildcard_to_regex,
)
from navigate.util.numeric import (
    ROUND_OFF,
    TOLERANCE,
    calculate_compound_growth,
    calculate_inertia,
    derive_smoothing_alpha,
    divide_nonzero,
    find_nearest,
    get_increment_origin_index,
    get_increments_origin_index,
    is_non_strictly_increasing,
    is_strictly_increasing,
    normalize_fractional,
    to_numpy,
    update_belief_path,
)
