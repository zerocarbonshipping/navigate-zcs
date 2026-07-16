# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_bulk_carrier_26k_dwt_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	30
		"01-01-2027"	66
		"01-01-2028"	82
		"01-01-2029"	88
	]

	Extrapolate = FLAT
}
