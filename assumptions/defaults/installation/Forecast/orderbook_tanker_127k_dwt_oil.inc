# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_tanker_127k_dwt_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	83
		"01-01-2027"	172
		"01-01-2028"	276
		"01-01-2029"	328
		"01-01-2030"	330
	]

	Extrapolate = FLAT
}
