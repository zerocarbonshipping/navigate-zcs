# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_container_15000_teu_methane" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	45
		"01-01-2027"	66
		"01-01-2028"	140
		"01-01-2029"	266
		"01-01-2030"	317
		"01-01-2031"	322
	]

	Extrapolate = FLAT
}
