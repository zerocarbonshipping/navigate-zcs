# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.assign import (
    assign_fraction_list,
    assign_id,
    assign_id_list,
    assign_integer,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
    expand_id_wildcard,
)
from navigate.core.expression import Expression
from navigate.core.node_reference import NodeReference
from navigate.core.scalar import Scalar
from navigate.core.wrap import as_list, as_scalar, as_scalar_list
