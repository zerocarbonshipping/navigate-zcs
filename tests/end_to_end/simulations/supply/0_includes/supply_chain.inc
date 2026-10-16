# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Oil from the liquid market at a pinned price, and e-ammonia from one
# producer with two plants that are identical but for their region: the
# renewable electricity costs 50 USD/MWh in Europe and 80 in the Middle East,
# so the European plant has the lower levelized cost of fuel. Every economic
# and sizing input is pinned (rounded from the installation defaults); WTT
# emissions are pinned at the ports.
Import Fuel "fossil_fuel_oil"
Import Fuel "ammonia_electro"

Import Port "port_global"
Import Port "port_europe"

Port "*" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("ammonia_electro", TRUE)

	set_bunker_price_overwrite("fossil_fuel_oil", 550)                   # USD/ton
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", 0.8)   # ton/ton fuel
	set_bunker_wtt_overwrite("ammonia_electro", "carbon_dioxide", 0.)
}

Copy Plant "plant_ammonia_electro_alkaline" "plant_ammonia_europe"
Copy Plant "plant_ammonia_electro_alkaline" "plant_ammonia_middle_east"

Plant "plant_ammonia_europe" {
	Region = Region("europe")
	Source = Source("renewable")
	Capacity = 1000      # ton/day
	LeadTime = 1         # years
	Lifetime = 30        # years
	Uptime = 0.9
}

Plant "plant_ammonia_middle_east" {
	Region = Region("middle_east")
	Source = Source("renewable")
	Capacity = 1000      # ton/day
	LeadTime = 1         # years
	Lifetime = 30        # years
	Uptime = 0.9
}

Producer "epc_ammonia" {
	Plants = [
		Plant("plant_ammonia_europe"),
		Plant("plant_ammonia_middle_east")
	]

	FuelDemandSensitivity = 1.25
	FuelCostSensitivity = 0.5
	InitialCapacity = [5000, 5000]                # ton/day
	MaximumDevelopment = 1e6
	JumpStartFraction = 1.0

	set_export_distribution("port_global", 1.)
}

Import Source "renewable"
Import Process "electrolysis_stack_alkaline"
Import Process "ammonia_synthesis_electro_alkaline"
Import Process "hydrogen_electro_alkaline"
Import Process "nitrogen_air_separation"
Import Feedstock "demineralized_water"

# Defined here rather than imported, so the default regions' prices of
# unrelated feedstocks stay out of the deck.
Region "europe" {
	set_source_opex("renewable", 50)                # USD/MWh
}

Region "middle_east" {
	set_source_opex("renewable", 80)                # USD/MWh
}

# the same production economics in both regions (USD/ton unless noted)
Region "*" {
	set_feedstock_cost("demineralized_water", 2)

	set_process_capex("electrolysis_stack_alkaline", 4000)
	set_process_opex("electrolysis_stack_alkaline", 160)
	set_process_energy("electrolysis_stack_alkaline", 51)    # MWh/ton
	set_process_lifetime("electrolysis_stack_alkaline", 10)  # years
	set_process_replacement("electrolysis_stack_alkaline", 0.2)

	set_process_capex("hydrogen_electro_alkaline", 3600)
	set_process_opex("hydrogen_electro_alkaline", 145)
	set_process_energy("hydrogen_electro_alkaline", 4.0)     # MWh/ton
	set_process_lifetime("hydrogen_electro_alkaline", 20)    # years
	set_process_replacement("hydrogen_electro_alkaline", 0.2)

	set_process_capex("ammonia_synthesis_electro_*", 900)
	set_process_opex("ammonia_synthesis_electro_*", 40)
	set_process_energy("ammonia_synthesis_electro_*", 0.44)  # MWh/ton
}
