# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-ammonia production plant (mid).
# Unit: ton / day

Forecast "ammonia_electro_plant_capacity_mid" {
	Table = [
		"01-01-2025"	116
		"01-01-2026"	368
		"01-01-2027"	628
		"01-01-2028"	895
		"01-01-2029"	1173
		"01-01-2030"	1464
		"01-01-2031"	1768
		"01-01-2032"	2091
		"01-01-2033"	2434
		"01-01-2034"	2802
		"01-01-2035"	3200
		"01-01-2036"	3633
		"01-01-2037"	4110
		"01-01-2050"	4110
	]

	Extrapolate = FLAT
}
