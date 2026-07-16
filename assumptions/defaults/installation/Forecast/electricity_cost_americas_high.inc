# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Levelized cost of electricity in Americas (high case).
# Unit: USD / MWh / year


Forecast "electricity_cost_americas_high" {
	Table = [
		"01-01-2025"	91.2
		"01-01-2026"	74.1
		"01-01-2027"	70.7
		"01-01-2028"	66.1
		"01-01-2029"	63.6
		"01-01-2030"	61.1
		"01-01-2031"	58.5
		"01-01-2032"	56.6
		"01-01-2033"	54.8
		"01-01-2034"	53.0
		"01-01-2035"	55.9
		"01-01-2036"	55.2
		"01-01-2037"	54.7
		"01-01-2038"	54.5
		"01-01-2039"	54.2
		"01-01-2040"	53.4
		"01-01-2041"	53.1
		"01-01-2042"	52.8
		"01-01-2043"	52.7
		"01-01-2044"	52.3
		"01-01-2045"	51.7
		"01-01-2046"	51.3
		"01-01-2047"	50.9
		"01-01-2048"	50.3
		"01-01-2049"	50.0
		"01-01-2050"	49.4
	]
	
	Extrapolate = LINEAR
}
