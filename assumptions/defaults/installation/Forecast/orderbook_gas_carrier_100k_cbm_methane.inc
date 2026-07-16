# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Orderbook of cumulative vessels that is supposed to have entered the fleet in a given year.
# Unit: Number of vessels

Forecast "orderbook_gas_carrier_100k_cbm_methane" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	73
		"01-01-2027"	142
		"01-01-2028"	251
		"01-01-2029"	313
		"01-01-2030"	322
		"01-01-2031"	328
		"01-01-2032"	334
	]

	Extrapolate = FLAT
}
