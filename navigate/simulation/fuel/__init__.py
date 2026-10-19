# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fuel-supply domain: production, delivery, port supply and producer planning."""

from __future__ import annotations

from navigate.simulation.fuel.decommission import (
    perform_decommissioning,
    update_plant_ages,
)
from navigate.simulation.fuel.expectation import (
    calculate_export_expectations,
    calculate_port_expectations,
    calculate_producer_evolution_expectation,
)
from navigate.simulation.fuel.feed import calculate_feed_availability
from navigate.simulation.fuel.initialization import initialize_existing_producer
from navigate.simulation.fuel.logistics import calculate_plant_logistics_expectations
from navigate.simulation.fuel.pipeline import (
    perform_pipeline_delivery,
    perform_pipeline_planning,
)
from navigate.simulation.fuel.port_supply import calculate_fuel_import_to_ports
from navigate.simulation.fuel.production import calculate_plant_production_expectations
from navigate.simulation.fuel.profile import (
    calculate_plant_profile,
    calculate_port_profile,
    calculate_producer_profile,
)
from navigate.simulation.fuel.results import (
    complete_global_fuel_results,
    complete_plant_profile,
    complete_port_profile,
    complete_producer_profile,
)
from navigate.simulation.fuel.supply_demand import (
    calculate_constrained_fair_share_fuel_demand,
    calculate_development_potential,
    calculate_expected_fuel_demand,
    calculate_expected_fuel_supply,
    calculate_fuel_supply_demand_gap,
)
