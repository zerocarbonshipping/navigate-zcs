# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Europe (mid case).
# Unit: USD / MWh / year


Forecast "electricity_cost_europe_mid" {
	Table = [
		"01-01-2025"	77.1
		"01-01-2026"	72.1
		"01-01-2027"	69.2
		"01-01-2028"	72.1
		"01-01-2029"	70.9
		"01-01-2030"	70.9
		"01-01-2031"	68.8
		"01-01-2032"	67.4
		"01-01-2033"	66.1
		"01-01-2034"	64.8
		"01-01-2035"	63.7
		"01-01-2036"	62.6
		"01-01-2037"	61.6
		"01-01-2038"	60.6
		"01-01-2039"	59.7
		"01-01-2040"	58.8
		"01-01-2041"	57.9
		"01-01-2042"	57.1
		"01-01-2043"	56.4
		"01-01-2044"	55.8
		"01-01-2045"	55.2
		"01-01-2046"	54.6
		"01-01-2047"	54.0
		"01-01-2048"	53.5
		"01-01-2049"	53.2
		"01-01-2050"	52.7
	]
	
	Extrapolate = LINEAR
}
