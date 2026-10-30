# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# REPORT - numbers per vessel type and fleet, besides DefaultReport's global sheet.

Report "output" {
	Directory = "./reports"

	add_vessel_property("rhine_*", ConsumedEnergy)
	add_vessel_property("rhine_*", ActualSpeed)
	add_vessel_property("rhine_*", CargoMiles)
	add_vessel_property("rhine_*", InvestmentFreightRate)
	add_vessel_property("rhine_*", InstantaneousFreightRate)

	add_fleet_property("rhine_fleet", ExistingVessels)
	add_fleet_property("rhine_fleet", Newbuilds)
	add_fleet_property("rhine_fleet", FuelExpenses)
	add_fleet_property("rhine_fleet", RegulationExpenses)
	add_fleet_property("rhine_fleet", TotalConsumedMass)

	# delivered bunker price per unit of energy, by port
	add_port_property("*", BunkerIntensityPrice)

	# levelised cost per GJ of each plant, even when none is built
	add_plant_property("*", InvestmentIntensityCost)
}
