# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Default ports; Load DefaultPort is not used because it also overwrites the
# LNG bunker price, and this deck has no LNG fuel node.
Import Port "port_global"
Import Port "port_europe"

Port "*" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("ammonia_electro", TRUE)

	# oil is not calculated bottom-up: overwrite its price and WTT
	set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))
}

BunkerLogistics {
	# oil is a liquid market fuel: available without a Producer
	LiquidMarketFuels = [Fuel("fossil_fuel_oil")]

	set_distance("*", "*", 1000)
	set_transport_cost("*", 0.1)
}
