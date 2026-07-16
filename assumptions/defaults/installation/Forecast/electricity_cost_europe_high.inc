# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Europe (high case).
# Unit: USD / MWh / year


Forecast "electricity_cost_europe_high" {
	Table = [
		"01-01-2025"	92.5
		"01-01-2026"	86.5
		"01-01-2027"	83.1
		"01-01-2028"	86.6
		"01-01-2029"	85.1
		"01-01-2030"	85.1
		"01-01-2031"	82.6
		"01-01-2032"	80.9
		"01-01-2033"	79.4
		"01-01-2034"	77.7
		"01-01-2035"	76.5
		"01-01-2036"	75.1
		"01-01-2037"	73.9
		"01-01-2038"	72.8
		"01-01-2039"	71.7
		"01-01-2040"	70.6
		"01-01-2041"	69.5
		"01-01-2042"	68.5
		"01-01-2043"	67.7
		"01-01-2044"	66.9
		"01-01-2045"	66.2
		"01-01-2046"	65.5
		"01-01-2047"	64.8
		"01-01-2048"	64.2
		"01-01-2049"	63.8
		"01-01-2050"	63.2
	]
	
	Extrapolate = LINEAR
}
