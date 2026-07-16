# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Asia (low case).
# Unit: USD / MWh / year


Forecast "electricity_cost_asia_low" {
	Table = [
		"01-01-2025"	76.6
		"01-01-2026"	70.3
		"01-01-2027"	65.2
		"01-01-2028"	61.5
		"01-01-2029"	58.1
		"01-01-2030"	55.3
		"01-01-2031"	52.7
		"01-01-2032"	50.5
		"01-01-2033"	48.5
		"01-01-2034"	46.9
		"01-01-2035"	45.5
		"01-01-2036"	44.4
		"01-01-2037"	43.5
		"01-01-2038"	42.5
		"01-01-2039"	41.6
		"01-01-2040"	40.8
		"01-01-2041"	40.1
		"01-01-2042"	39.4
		"01-01-2043"	38.7
		"01-01-2044"	38.1
		"01-01-2045"	37.4
		"01-01-2046"	36.8
		"01-01-2047"	36.1
		"01-01-2048"	35.5
		"01-01-2049"	34.8
		"01-01-2050"	34.2
	]
	
	Extrapolate = LINEAR
}
