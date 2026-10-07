# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fuel-supply domain: production, delivery, port supply and producer planning."""

from __future__ import annotations

from navigate.simulation.fuel.aggregation import calculate_producer_profile
from navigate.simulation.fuel.evolution import (
    calculate_export_expectation,
    perform_planning,
    perform_progression,
)
from navigate.simulation.fuel.initialization import initialize_existing_producer
from navigate.simulation.fuel.logistics import calculate_plant_logistics_expectations
from navigate.simulation.fuel.port_supply import calculate_fuel_import_to_ports
from navigate.simulation.fuel.production import calculate_plant_production_expectations
from navigate.simulation.fuel.supply_demand import (
    calculate_constrained_fair_share_fuel_demand,
    calculate_development_potential,
    calculate_expected_fuel_demand,
    calculate_expected_fuel_supply,
    calculate_fuel_supply_demand_gap,
)
