# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.fleet.aggregation import calculate_fleet_profile
from navigate.fleet.beliefs import (
    record_investment_signals,
    update_regulation_flexibility_beliefs,
    update_vessel_scarcity_beliefs,
)
from navigate.fleet.charter import calculate_cargo_charter_properties, calculate_vessel_charter_properties
from navigate.fleet.evolution import calculate_evolution_expectation, perform_fleet_evolution
from navigate.fleet.fuel_option import (
    determine_fuel_type,
    determine_usable_fuel_types,
    determine_usable_fuels,
    get_fuels_per_fuel_type,
)
from navigate.fleet.operation import convert_to_regional_steps, update_operational_profile
from navigate.fleet.post_process import post_process_investment_metric
from navigate.fleet.speed import perform_speed_management
from navigate.fleet.technology import perform_technology_installation
from navigate.fleet.utils import net_energy_from_raw
