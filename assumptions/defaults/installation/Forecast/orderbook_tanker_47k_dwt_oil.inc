# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_tanker_47k_dwt_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	114
		"01-01-2027"	318
		"01-01-2028"	486
		"01-01-2029"	543
		"01-01-2030"	553
		"01-01-2031"	561
		"01-01-2032"	562
	]

	Extrapolate = FLAT
}
