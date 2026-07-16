# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Middle East (low case).
# Unit: USD / MWh / year


Forecast "electricity_cost_middle_east_low" {
	Table = [
		"01-01-2025"	49.6
		"01-01-2026"	46.3
		"01-01-2027"	44.1
		"01-01-2028"	42.2
		"01-01-2029"	40.4
		"01-01-2030"	38.9
		"01-01-2031"	37.8
		"01-01-2032"	36.8
		"01-01-2033"	35.8
		"01-01-2034"	34.9
		"01-01-2035"	34.1
		"01-01-2036"	33.4
		"01-01-2037"	32.6
		"01-01-2038"	31.9
		"01-01-2039"	31.2
		"01-01-2040"	30.6
		"01-01-2041"	30.0
		"01-01-2042"	29.4
		"01-01-2043"	28.9
		"01-01-2044"	28.3
		"01-01-2045"	27.8
		"01-01-2046"	27.2
		"01-01-2047"	26.7
		"01-01-2048"	26.2
		"01-01-2049"	25.7
		"01-01-2050"	25.3
	]
	
	Extrapolate = LINEAR
}
