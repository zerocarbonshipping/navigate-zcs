# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# REPORT - one Excel file per run, for comparing the scenarios.

Report "output" {
	Directory = "./reports"

	add_fleet_property("*", ExistingVessels)
	add_fleet_property("*", Newbuilds)
	add_fleet_property("*", FuelConversions)
	add_fleet_property("*", FuelTypeEnergy)
	add_fleet_property("*", TotalEquivalentWTW)
	add_fleet_property("*", FuelExpenses)
	add_fleet_property("*", RegulationExpenses)

	add_port_property("*", BunkerIntensityPrice)
}
