# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_bulk_carrier_200k_dwt_methanol" {
	Table = [
		"01-01-2025"	0
		"01-01-2027"	1
		"01-01-2028"	2
	]

	Extrapolate = FLAT
}
