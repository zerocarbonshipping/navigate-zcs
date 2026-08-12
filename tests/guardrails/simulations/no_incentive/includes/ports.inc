# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# The default ports (port_global, port_europe) are loaded by the .nav via
# Load DefaultPort, which also overwrites bunker prices for oil and LNG.
Port "*" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", TRUE)
	set_bunkering_allowed("methanol_bio", TRUE)
	set_bunkering_allowed("ammonia_electro", TRUE)
}

BunkerLogistics {
	# oil and LNG are liquid market fuels: available without a Producer
	LiquidMarketFuels = [Fuel("fossil_fuel_oil"), Fuel("liquefied_natural_gas")]

	set_distance("*", "*", 1000)
	set_transport_cost("*", 0.1)
}
