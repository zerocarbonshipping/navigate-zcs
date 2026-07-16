# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Asia (mid case).
# Unit: USD / MWh / year


Forecast "electricity_cost_asia_mid" {
	Table = [
		"01-01-2025"	95.7
		"01-01-2026"	87.8
		"01-01-2027"	81.5
		"01-01-2028"	76.9
		"01-01-2029"	72.6
		"01-01-2030"	69.1
		"01-01-2031"	65.8
		"01-01-2032"	63.1
		"01-01-2033"	60.7
		"01-01-2034"	58.6
		"01-01-2035"	56.9
		"01-01-2036"	55.6
		"01-01-2037"	54.3
		"01-01-2038"	53.2
		"01-01-2039"	52.1
		"01-01-2040"	51.0
		"01-01-2041"	50.1
		"01-01-2042"	49.3
		"01-01-2043"	48.4
		"01-01-2044"	47.6
		"01-01-2045"	46.7
		"01-01-2046"	46.0
		"01-01-2047"	45.1
		"01-01-2048"	44.3
		"01-01-2049"	43.5
		"01-01-2050"	42.8
	]
	
	Extrapolate = LINEAR
}
