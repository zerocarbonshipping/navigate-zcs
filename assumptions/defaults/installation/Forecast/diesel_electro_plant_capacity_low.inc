# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-diesel production plant (low).
# Unit: ton / day

Forecast "diesel_electro_plant_capacity_low" {
	Table = [
		"01-01-2025"	19
		"01-01-2026"	21
		"01-01-2027"	23
		"01-01-2028"	26
		"01-01-2029"	30
		"01-01-2030"	35
		"01-01-2031"	41
		"01-01-2032"	48
		"01-01-2033"	56
		"01-01-2034"	66
		"01-01-2035"	78
		"01-01-2036"	93
		"01-01-2037"	111
		"01-01-2038"	133
		"01-01-2039"	159
		"01-01-2040"	192
		"01-01-2041"	231
		"01-01-2042"	279
		"01-01-2043"	339
		"01-01-2044"	411
		"01-01-2050"	411
	]

	Extrapolate = FLAT
}
