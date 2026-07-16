# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_container_4500_teu_methane" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	3
		"01-01-2027"	4
		"01-01-2028"	6
	]

	Extrapolate = FLAT
}
