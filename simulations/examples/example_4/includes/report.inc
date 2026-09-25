# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# REPORT - Excel export, for inspecting the numbers without the Python API.
#
# A CamelCase property resolves to the matching getter on the node's profile:
# InvestmentFreightRate reads profile.get_investment_freight_rate(). Anything
# with a getter on the profile can be exported this way.

Report "output" {
	Directory = "./reports"

	# transport cost, USD/cargo-mile. Investment = forward-looking levelized cost,
	# the number the choice model compares; Instantaneous = what the year cost.
	add_vessel_property("ship_*", InvestmentFreightRate)
	add_vessel_property("ship_*", InstantaneousFreightRate)

	# what the cargo owner pays per year, USD
	add_vessel_property("ship_*", CargoCharterRate)

	# operational response: did it slow down instead of switching fuel?
	add_vessel_property("ship_*", ActualSpeed)
	add_vessel_property("ship_*", CargoMiles)

	# fleet composition: how many ships of each type exist, and what got ordered
	add_fleet_property("copper_trade", ExistingVessels)
	add_fleet_property("copper_trade", Newbuilds)
	add_fleet_property("copper_trade", FuelConversions)

	# energy efficiency. TechnologyUptake is keyed by (vessel, technology), so it
	# needs a reduction; the third argument is positional, not `reduce=`.
	add_fleet_property("copper_trade", TechnologyUptake, BOTH)
	add_fleet_property("copper_trade", TechnologyExpenses)
	add_fleet_property("copper_trade", TechnologyEnergyIntensitySaving)

	# where the money went
	add_fleet_property("copper_trade", FuelExpenses)
	add_fleet_property("copper_trade", RegulationExpenses)
	add_fleet_property("copper_trade", RemedialExpenses)

	# delivered bunker price per unit of energy, by port
	add_port_property("*", BunkerIntensityPrice)
}
