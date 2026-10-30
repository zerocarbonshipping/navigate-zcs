# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# BUNKER LOGISTICS - from where a fuel is made to the port that sells it.
# Fossil fuels are global commodities with a quoted price; the new fuels pay
# distance x rate.

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil"), Fuel("liquefied_natural_gas")]

	# Trinidad's plants, at Point Lisas, to each port (nm, the route.inc legs)
	set_distance("caribbean", "trinidad", 15)      # Point Lisas - Port of Spain
	set_distance("caribbean", "martinique", 278)
	set_distance("caribbean", "jamaica", 1100)

	# INVENTED: fuels from the US Gulf Coast (Houston)
	set_distance("americas", "jamaica", 1300)
	set_distance("americas", "martinique", 2000)
	set_distance("americas", "trinidad", 2100)

	# Magallanes to each port through the Panama Canal, measured along a sea
	# route drawn offshore (the Atlantic route is longer: 5,560 nm to Trinidad).
	# Canal tolls are not counted.
	set_distance("chile", "jamaica", 4700)
	set_distance("chile", "trinidad", 5250)
	set_distance("chile", "martinique", 5250)

	# INVENTED: USD per ton per nautical mile, the rate example_4 invented too
	set_transport_cost("*", 0.02)
}
