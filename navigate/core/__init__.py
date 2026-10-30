# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The model definition.

The node classes a deck declares, the DSL value infrastructure their setters are
written against, and the containers holding their dynamic state and output.
"""

from __future__ import annotations

from navigate.core.assign import (
    assign_boolean,
    assign_bound,
    assign_date,
    assign_fraction_list,
    assign_id,
    assign_id_list,
    assign_integer,
    assign_list,
    assign_member,
    assign_reference,
    assign_reference_list,
    assign_value,
    check_forecast_is_cumulative,
    check_lengths_match,
    check_tables_are_finite,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.dsl import SECTION_DEFINE, deck_attribute, deck_command
from navigate.core.expression import Expression
from navigate.core.node_maps import (
    define_vessel_fuel_maps,
    define_vessels_in_jurisdiction,
    update_bunkerable_fuels,
    update_imposed_levies,
)
from navigate.core.scalar import Scalar
from navigate.core.wrap import as_list, as_scalar
