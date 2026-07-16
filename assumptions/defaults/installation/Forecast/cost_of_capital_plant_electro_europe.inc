# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for a e-fuels plant in Europe.
# Unit: fraction / year

Forecast "cost_of_capital_plant_electro_europe" {
	Table = [
		"01-01-2025"	0.100
		"01-01-2030"	0.100
		"01-01-2035"	0.096
		"01-01-2040"	0.086
		"01-01-2045"	0.074
		"01-01-2050"	0.061
	]
	
	Extrapolate = LINEAR
}
