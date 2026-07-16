# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_cruise_175k_gt_methane" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	5
		"01-01-2027"	6
		"01-01-2028"	10
		"01-01-2029"	13
		"01-01-2030"	15
		"01-01-2031"	17
		"01-01-2032"	20
		"01-01-2033"	21
		"01-01-2034"	22
	]

	Extrapolate = FLAT
}
