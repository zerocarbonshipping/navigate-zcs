# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for a e-fuels plant in Americas (based on North America).
# Unit: fraction / year

Forecast "cost_of_capital_plant_electro_americas" {
	Table = [
		"01-01-2025"	0.099
		"01-01-2030"	0.099
		"01-01-2035"	0.095
		"01-01-2040"	0.087
		"01-01-2045"	0.074
		"01-01-2050"	0.063
	]
	
	Extrapolate = LINEAR
}
