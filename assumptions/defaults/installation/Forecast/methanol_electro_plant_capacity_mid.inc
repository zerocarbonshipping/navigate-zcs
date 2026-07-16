# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-methanol production plant (mid).
# Unit: ton / day

Forecast "methanol_electro_plant_capacity_mid" {
	Table = [
		"01-01-2025"	188
		"01-01-2026"	457
		"01-01-2027"	736
		"01-01-2028"	1027
		"01-01-2029"	1330
		"01-01-2030"	1650
		"01-01-2031"	1989
		"01-01-2032"	2350
		"01-01-2033"	2737
		"01-01-2034"	3155
		"01-01-2035"	3611
		"01-01-2036"	4110
		"01-01-2050"	4110
	]

	Extrapolate = FLAT
}
