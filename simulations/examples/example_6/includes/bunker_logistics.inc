# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# BUNKER LOGISTICS - every fuel is a market fuel, priced at the ports
# (includes/ports.inc). Nothing is made in the deck, so nothing is delivered.

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil"), Fuel("liquefied_natural_gas"),
	                     Fuel("fatty_acid_methyl_ester"), Fuel("diesel_electro"),
	                     Fuel("methanol_electro")]
}
