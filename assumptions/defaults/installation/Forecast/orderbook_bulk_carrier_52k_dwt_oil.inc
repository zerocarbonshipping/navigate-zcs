# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_bulk_carrier_52k_dwt_oil" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	285
		"01-01-2027"	553
		"01-01-2028"	730
		"01-01-2029"	784
		"01-01-2030"	792
	]

	Extrapolate = FLAT
}
