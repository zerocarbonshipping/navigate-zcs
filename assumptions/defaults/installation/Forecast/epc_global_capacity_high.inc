# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of how many electro/blue fuel production plants can be built in a given year (high case).
# Unit: plants / year

Forecast "epc_global_capacity_high" {
	Table = [
		"01-01-2024"	13
		"01-01-2050"	125.67
	]
	
	Extrapolate=LINEAR
}
