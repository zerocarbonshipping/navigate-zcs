# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Supply chain: Source, Feedstock, Process, Transport, Region, Plant, Producer
#
# Attributes covered:
#   Source:    Dependency
#   Feedstock: (none - empty)
#   Process:   Feeds, Conversions
#   Transport: (none - empty)
#   Plant:     Fuel, Process, Source, Region, CostOfCapital, Capacity, Uptime,
#              Lifetime, LeadTime
#   Producer:  Plants, InitialCapacity, InitialAgeDistribution, Inertia,
#              MinimumOfftakeDuration, FuelDemandSensitivity, FuelCostSensitivity,
#              MaximumDevelopment, MaximumRampUp, JumpStartFraction
#   Region:    (none - only commands)
#
# Commands covered:
#   Plant:    set_feed_transport, set_feed_distance
#   Producer: set_existing_pipeline, set_allow_plant, set_feed_constraint,
#             set_export_distribution
#   Region:   set_process_capex, set_process_opex, set_process_energy,
#             set_process_lifetime, set_process_replacement, set_process_wtt,
#             set_source_capex, set_source_opex, set_source_wtt,
#             set_feedstock_cost, set_feedstock_wtt,
#             set_transport_cost, set_transport_wtt

Source "source_renewable" {
	Dependency = CONNECTED
}

Source "source_grid" {
	Dependency = STANDALONE
}

Feedstock "water" {
}

Feedstock "co2_bio" {
}

Process "methanol_synthesis" {
	Feeds = [Feedstock("water"), Feedstock("co2_bio")]
	Conversions = [4.5, 2.75]
}

Transport "truck" {
}

Region "region_a" {
	set_process_capex("methanol_synthesis", 180)
	set_process_opex("methanol_synthesis", 100)
	set_process_energy("methanol_synthesis", 0.52)
	set_process_lifetime("methanol_synthesis", 25)
	set_process_replacement("methanol_synthesis", 0.5)
	set_process_wtt("methanol_synthesis", "carbon_dioxide", -1.35)
	set_source_capex("source_renewable", 500)
	set_source_opex("source_renewable", 50)
	set_source_wtt("source_renewable", "carbon_dioxide", 0)
	set_feedstock_cost("water", 1)
	set_feedstock_wtt("water", "carbon_dioxide", 0)
	set_transport_cost("truck", 10)
	set_transport_wtt("truck", "carbon_dioxide", 0.1)
}

Plant "plant_methanol" {
	Fuel = Fuel("bio_methanol")
	Process = Process("methanol_synthesis")
	Source = Source("source_renewable")
	Region = Region("region_a")
	CostOfCapital = 0.08
	Capacity = 1000
	Uptime = 0.9
	Lifetime = 25
	LeadTime = 4
	set_feed_transport("water", Transport("truck"))
	set_feed_distance("water", 100)
}

Producer "producer_global" {
	Plants = [Plant("plant_methanol")]
	InitialCapacity = [500]
	InitialAgeDistribution = [Curve("curve_plant_age")]
	Inertia = 0.1
	MinimumOfftakeDuration = 1
	FuelDemandSensitivity = 1.25
	FuelCostSensitivity = 0.5
	MaximumDevelopment = 5
	MaximumRampUp = 0.5
	JumpStartFraction = 0.1
	set_existing_pipeline("plant_methanol", Forecast("fc_pipeline"))
	set_allow_plant("plant_methanol", TRUE)
	set_feed_constraint("water", 1e6)
	set_export_distribution("port_a", 1.0)
}
