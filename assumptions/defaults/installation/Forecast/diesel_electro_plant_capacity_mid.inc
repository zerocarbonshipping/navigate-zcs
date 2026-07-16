# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-diesel production plant (mid).
# Unit: ton / day

Forecast "diesel_electro_plant_capacity_mid" {
	Table = [
		"01-01-2025"	19
		"01-01-2026"	46
		"01-01-2027"	74
		"01-01-2028"	103
		"01-01-2029"	133
		"01-01-2030"	165
		"01-01-2031"	199
		"01-01-2032"	235
		"01-01-2033"	274
		"01-01-2034"	316
		"01-01-2035"	361
		"01-01-2036"	411
		"01-01-2050"	411
	]

	Extrapolate = FLAT
}
