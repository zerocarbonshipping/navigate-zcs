# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# BUNKER LOGISTICS - production site to bunker port.
# LiquidMarketFuels are treated as global commodities: quoted price, no plant,
# no producer, no logistics chain. Everything else picks up distance x rate.

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil"), Fuel("liquefied_natural_gas")]

	# The values have been invented for this example:
	# nautical miles from the production region to each port
	set_distance("americas", "san_antonio", 1250)
	set_distance("americas", "rotterdam", 7600)
	set_distance("europe", "rotterdam", 540)
	set_distance("europe", "san_antonio", 7600)

	# USD per ton per nautical mile
	set_transport_cost("*", 0.02)
}
