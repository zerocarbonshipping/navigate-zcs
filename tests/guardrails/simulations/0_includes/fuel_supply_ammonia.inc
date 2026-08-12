# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# E-ammonia supply chain, shared by the two supply decks. MaximumDevelopment
# is a deck-sizing input (tuned): the value below keeps supply permanently
# behind the regulation-imposed demand (supply_constrained);
# supply_then_demand_constrained overrides it in its own includes/ so supply
# catches up mid-simulation.

Import Fuel "fossil_fuel_oil"

Import Fuel "ammonia_electro"

Import Plant "plant_ammonia_electro_alkaline"

Plant "plant_ammonia_electro_alkaline" {
	Region = Region("europe")
	Source = Source("renewable")
}

Import Process "electrolysis_stack_alkaline"
Import Process "ammonia_synthesis_electro_alkaline"
Import Process "hydrogen_electro_alkaline"
Import Process "nitrogen_air_separation"
Import Feedstock "demineralized_water"

# decision sensitivities come from Load DefaultCalibration in the .nav
Producer "epc_europe" {
	Plants = [Plant("plant_ammonia_electro_alkaline")]

	MaximumDevelopment = 1

	# no artificial utilization ramp at simulation start: the deck asserts
	# that development is pinned to the constraint from the first step
	JumpStartFraction = 1.0

	set_export_distribution("port_global", 1.)
}

# --------------------------- REGION AND SOURCES ------------------------------
Import Source "renewable"
Import Transport "truck"

Region "europe" {
	# energy source cost
	set_source_opex("renewable", Forecast("electricity_cost_europe_mid"))

	# feedstock cost
	set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))

	# e-hydrogen (alkaline)
	set_process_capex("electrolysis_stack_alkaline", Timetable("electrolysis_stack_alkaline_capex"))
	set_process_opex("electrolysis_stack_alkaline", Timetable("electrolysis_stack_alkaline_opex"))
	set_process_energy("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_energy"))
	set_process_lifetime("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_lifetime"))
	set_process_replacement("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_replacement"))

	set_process_capex("hydrogen_electro_alkaline", Timetable("hydrogen_electro_alkaline_capex"))
	set_process_opex("hydrogen_electro_alkaline", Timetable("hydrogen_electro_alkaline_opex"))
	set_process_energy("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_energy"))
	set_process_lifetime("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_lifetime"))
	set_process_replacement("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_replacement"))

	# e-ammonia
	set_process_capex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_capex"))
	set_process_opex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_opex"))
	set_process_energy("ammonia_synthesis_electro_*", Forecast("ammonia_synthesis_energy"))
}

Region "*" {
	set_transport_cost("truck", 0.0)
	set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))
}
