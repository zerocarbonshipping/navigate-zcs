# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.fuel.aggregation import calculate_producer_profile
from navigate.fuel.logistics import calculate_plant_logistics_expectations
from navigate.fuel.port_supply import calculate_fuel_import_to_ports
from navigate.fuel.production import calculate_plant_production_expectations
from navigate.fuel.supply_demand import (
    calculate_constrained_fair_share_fuel_demand,
    calculate_expected_fuel_demand,
    calculate_expected_fuel_supply,
    calculate_fuel_supply_demand_gap,
)
from navigate.fuel.utils import calculate_development_potential
