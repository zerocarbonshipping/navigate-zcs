# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Europe (low case).
# Unit: USD / MWh / year


Forecast "electricity_cost_europe_low" {
	Table = [
		"01-01-2025"	61.7
		"01-01-2026"	57.7
		"01-01-2027"	55.4
		"01-01-2028"	57.7
		"01-01-2029"	56.7
		"01-01-2030"	56.7
		"01-01-2031"	55.0
		"01-01-2032"	53.9
		"01-01-2033"	52.9
		"01-01-2034"	51.8
		"01-01-2035"	51.0
		"01-01-2036"	50.1
		"01-01-2037"	49.3
		"01-01-2038"	48.5
		"01-01-2039"	47.8
		"01-01-2040"	47.0
		"01-01-2041"	46.3
		"01-01-2042"	45.7
		"01-01-2043"	45.1
		"01-01-2044"	44.6
		"01-01-2045"	44.1
		"01-01-2046"	43.7
		"01-01-2047"	43.2
		"01-01-2048"	42.8
		"01-01-2049"	42.5
		"01-01-2050"	42.1
	]
	
	Extrapolate = LINEAR
}
