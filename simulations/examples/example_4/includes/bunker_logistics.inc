# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# BUNKER LOGISTICS - production site to bunker port.
# LiquidMarketFuels such as fuel oil and LNG are treated as global commodities:
# available anywhere at a quoted price, with no plant, producer or logistics
# chain modelled. Everything else has to be physically moved from the plant to
# the bunker port, priced at distance x rate.

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil"), Fuel("liquefied_natural_gas")]

	# The values have been invented for this example:
	# the sea distance, in nautical miles, from each production region to each port
	set_distance("americas", "san_antonio", 1250)
	set_distance("americas", "rotterdam", 7600)
	set_distance("europe", "rotterdam", 540)
	set_distance("europe", "san_antonio", 7600)

	# USD per ton per nautical mile
	set_transport_cost("*", 0.02)
}
