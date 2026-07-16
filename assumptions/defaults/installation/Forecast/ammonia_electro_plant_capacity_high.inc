# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-ammonia production plant (high).
# Unit: ton / day

Forecast "ammonia_electro_plant_capacity_high" {
	Table = [
		"01-01-2025"	116
		"01-01-2026"	915
		"01-01-2027"	1714
		"01-01-2028"	2512
		"01-01-2029"	3311
		"01-01-2030"	4110
		"01-01-2050"	4110
	]

	Extrapolate = FLAT
}
