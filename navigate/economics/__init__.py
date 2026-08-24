# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.economics.decision import calculate_asset_shares, calculate_two_axis_uptake
from navigate.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    add_fixed_wtt,
    add_variable_opex,
    add_variable_wtt,
    as_equal_installments,
    build_cargo_flow,
    build_operating_age_flow,
    build_production_flow,
    correct_flow_residual,
    expand_to_flow,
    get_age_flow,
    get_flow_residual,
    get_flow_size,
    get_remaining_cost_flow,
    timeline_to_yearly,
)
from navigate.economics.metric import (
    calculate_age_levelized_cost,
    calculate_annualization_factor,
    calculate_levelized_cost,
    calculate_net_present_value,
)
