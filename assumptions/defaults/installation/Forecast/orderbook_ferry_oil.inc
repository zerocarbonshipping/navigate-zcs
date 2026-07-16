# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_ferry_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	163
		"01-01-2027"	257
		"01-01-2028"	275
		"01-01-2029"	284
		"01-01-2030"	290
		"01-01-2034"	291
	]

	Extrapolate = FLAT
}
