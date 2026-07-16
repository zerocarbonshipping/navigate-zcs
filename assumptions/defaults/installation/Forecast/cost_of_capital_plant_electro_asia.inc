# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for a e-fuels plant in Asia.
# Unit: fraction / year

Forecast "cost_of_capital_plant_electro_asia" {
	Table = [
		"01-01-2025"	0.121
		"01-01-2030"	0.121
		"01-01-2035"	0.118
		"01-01-2040"	0.111
		"01-01-2045"	0.101
		"01-01-2050"	0.061
	]
	
	Extrapolate = LINEAR
}
