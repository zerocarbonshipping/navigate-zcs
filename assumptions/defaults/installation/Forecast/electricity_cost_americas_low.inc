# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Americas (low case).
# Unit: USD / MWh / year


Forecast "electricity_cost_americas_low" {
	Table = [
		"01-01-2025"	60.8
		"01-01-2026"	49.4
		"01-01-2027"	47.1
		"01-01-2028"	44.1
		"01-01-2029"	42.4
		"01-01-2030"	40.7
		"01-01-2031"	39.0
		"01-01-2032"	37.8
		"01-01-2033"	36.5
		"01-01-2034"	35.3
		"01-01-2035"	37.3
		"01-01-2036"	36.8
		"01-01-2037"	36.5
		"01-01-2038"	36.3
		"01-01-2039"	36.1
		"01-01-2040"	35.6
		"01-01-2041"	35.4
		"01-01-2042"	35.2
		"01-01-2043"	35.1
		"01-01-2044"	34.8
		"01-01-2045"	34.5
		"01-01-2046"	34.2
		"01-01-2047"	33.9
		"01-01-2048"	33.5
		"01-01-2049"	33.3
		"01-01-2050"	33.0
	]
	
	Extrapolate = LINEAR
}
