# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_general_cargo_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	391
		"01-01-2027"	701
		"01-01-2028"	825
		"01-01-2029"	893
		"01-01-2030"	903
	]

	Extrapolate = FLAT
}
