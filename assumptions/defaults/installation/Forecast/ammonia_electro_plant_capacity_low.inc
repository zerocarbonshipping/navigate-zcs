# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-ammonia production plant (low).
# Unit: ton / day

Forecast "ammonia_electro_plant_capacity_low" {
	Table = [
		"01-01-2025"	116
		"01-01-2026"	163
		"01-01-2027"	210
		"01-01-2028"	263
		"01-01-2029"	324
		"01-01-2030"	396
		"01-01-2031"	480
		"01-01-2032"	578
		"01-01-2033"	693
		"01-01-2034"	826
		"01-01-2035"	982
		"01-01-2036"	1163
		"01-01-2037"	1373
		"01-01-2038"	1616
		"01-01-2039"	1898
		"01-01-2040"	2224
		"01-01-2041"	2600
		"01-01-2042"	3034
		"01-01-2043"	3534
		"01-01-2044"	4110
		"01-01-2050"	4110
	]

	Extrapolate = FLAT
}
