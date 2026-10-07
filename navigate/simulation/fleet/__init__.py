# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The fleet domain: operation, speed, charter, evolution and technology adoption."""

from __future__ import annotations

from navigate.simulation.fleet.aggregation import calculate_fleet_profile
from navigate.simulation.fleet.charter import (
    calculate_cargo_charter_properties,
    calculate_vessel_charter_properties,
)
from navigate.simulation.fleet.evolution import (
    calculate_evolution_expectation,
    perform_fleet_evolution,
)
from navigate.simulation.fleet.fuel_option import (
    determine_fuel_type,
    determine_usable_fuel_types,
    determine_usable_fuels,
)
from navigate.simulation.fleet.initialization import (
    assign_vessels_to_fleets,
    initialize_existing_fleet,
)
from navigate.simulation.fleet.operation import update_operational_profile
from navigate.simulation.fleet.post_process import (
    post_process_fleet_profile,
    post_process_investment_metric,
)
from navigate.simulation.fleet.power import verify_power_capacity
from navigate.simulation.fleet.scarcity_beliefs import (
    record_investment_signals,
    update_vessel_scarcity_beliefs,
)
from navigate.simulation.fleet.speed import perform_speed_management
from navigate.simulation.fleet.technology_adoption import (
    approximate_missing_technology,
    perform_technology_installation,
)
