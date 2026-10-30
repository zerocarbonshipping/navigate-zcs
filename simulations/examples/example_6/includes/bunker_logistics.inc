# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# BUNKER LOGISTICS - plant to bunker port. Fuel oil and LNG are market fuels.
# Plain numbers only, both INVENTED (listed in placeholders.inc as comments).

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil"), Fuel("liquefied_natural_gas")]

	# INVENTED: nautical miles from the European plants
	set_distance("europe", "duisburg", 400)
	set_distance("europe", "mannheim", 400)

	# INVENTED: USD per ton per nautical mile
	set_transport_cost("*", 0.03)
}
