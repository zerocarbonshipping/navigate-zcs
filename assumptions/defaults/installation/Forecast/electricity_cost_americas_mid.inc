# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Americas (mid case).
# Unit: USD / MWh / year


Forecast "electricity_cost_americas_mid" {
	Table = [
		"01-01-2025"	76.0
		"01-01-2026"	61.8
		"01-01-2027"	58.9
		"01-01-2028"	55.1
		"01-01-2029"	53.0
		"01-01-2030"	50.9
		"01-01-2031"	48.7
		"01-01-2032"	47.2
		"01-01-2033"	45.7
		"01-01-2034"	44.2
		"01-01-2035"	46.6
		"01-01-2036"	46.0
		"01-01-2037"	45.6
		"01-01-2038"	45.4
		"01-01-2039"	45.1
		"01-01-2040"	44.5
		"01-01-2041"	44.3
		"01-01-2042"	44.0
		"01-01-2043"	43.9
		"01-01-2044"	43.5
		"01-01-2045"	43.1
		"01-01-2046"	42.8
		"01-01-2047"	42.4
		"01-01-2048"	41.9
		"01-01-2049"	41.6
		"01-01-2050"	41.2
	]
	
	Extrapolate = LINEAR
}
