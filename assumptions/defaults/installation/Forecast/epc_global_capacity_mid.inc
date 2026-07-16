# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of how many electro/blue fuel production plants can be built in a given year (mid case).
# Unit: plants / year

Forecast "epc_global_capacity_mid" {
	Table = [
		"01-01-2024"	9.5
		"01-01-2050"	71.25
	]
	
	Extrapolate=LINEAR
}
