# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Output nodes: Report, Plot
#
# Attributes covered:
#   Report: Directory, FileFormat
#   Plot:   Directory
#
# Commands covered:
#   Report: add_property, add_fleet_property, add_levy_property,
#           add_plant_property, add_port_property, add_producer_property,
#           add_regulation_property, add_vessel_property
#   Plot:   add_plot

Report "report" {
	Directory = "./output/"
	FileFormat = XLSX
	add_property(TotalEquivalentWTW)
	add_property(ConsumedEnergy)
	add_fleet_property("fleet_a", ExistingVessels)
	add_fleet_property("fleet_a", Scrap)
	add_levy_property("levy_penalty", Collected)
	add_plant_property("plant_methanol", Production)
	add_port_property("port_a", BunkerSupply)
	add_producer_property("producer_global", Development)
	add_regulation_property("reg_absolute", VesselCompliance)
	add_vessel_property("vessel_oil", ConsumedEnergy)
}

Plot "test_plot" {
	Directory = "./output/"
	add_plot("global_emission_absolute")
	add_plot("global_fuel_consumed")
}
