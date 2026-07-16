# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_container_1500_teu_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	72
		"01-01-2027"	124
		"01-01-2028"	197
		"01-01-2029"	233
		"01-01-2030"	234
	]

	Extrapolate = FLAT
}
