# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Fuel supply for all four fuel types. Supply is deliberately ample
# (high MaximumDevelopment, no feed constraints): the deck isolates the
# newbuild choice model, so supply must never be the reason a fuel gets a
# small share.

# market fuels
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"

# ---------------------------- BIO-METHANOL -----------------------------------
Import Fuel "methanol_bio"

Import Plant "plant_methanol_bio_gasification"

Plant "plant_methanol_bio_gasification" {
	Region = Region("europe")
	Source = Source("grid")
}

Import Process "methanol_synthesis_bio_gasification"
Import Feedstock "feedstock_biomethanol_gasification"

# decision sensitivities come from Load DefaultCalibration in the .nav
Producer "producer_methanol" {
	Plants = [Plant("plant_methanol_bio_gasification")]

	MaximumDevelopment = 100
}

# --------------------------- ELECTRO-AMMONIA ---------------------------------
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

Producer "producer_ammonia" {
	Plants = [Plant("plant_ammonia_electro_alkaline")]

	MaximumDevelopment = 100
}

# all fuel is routed to the single bunkering hub
Producer "*" {
	set_export_distribution("port_global", 1.)
}

# --------------------------- REGION AND SOURCES ------------------------------
Import Source "grid"
Import Source "renewable"
Import Transport "truck"

Region "europe" {
	# energy source cost and emissions
	set_source_opex("grid", Forecast("electricity_cost_europe_mid"))
	set_source_opex("renewable", Forecast("electricity_cost_europe_mid"))
	set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_europe"))

	# feedstock costs
	set_feedstock_cost("feedstock_biomethanol_gasification", Forecast("feedstock_biomethanol_gasification_cost"))
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

	# bio-methanol
	set_process_capex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_capex"))
	set_process_opex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_opex"))
	set_process_energy("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_energy"))
	set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", <-Variable("carbon_dioxide_per_methanol")>)
}
