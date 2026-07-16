# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_general_cargo_methane" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	4
		"01-01-2028"	8
		"01-01-2029"	12
		"01-01-2030"	14
	]

	Extrapolate = FLAT
}
