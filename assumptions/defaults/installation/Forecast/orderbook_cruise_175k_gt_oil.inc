# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_cruise_175k_gt_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	1
		"01-01-2028"	2
		"01-01-2029"	3
		"01-01-2031"	4
		"01-01-2033"	5
		"01-01-2035"	6
		"01-01-2037"	7
	]

	Extrapolate = FLAT
}
