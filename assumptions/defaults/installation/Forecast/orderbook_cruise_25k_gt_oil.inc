# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_cruise_25k_gt_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	10
		"01-01-2027"	21
		"01-01-2028"	28
		"01-01-2029"	33
		"01-01-2030"	35
		"01-01-2031"	37
		"01-01-2032"	40
		"01-01-2033"	41
	]

	Extrapolate = FLAT
}
