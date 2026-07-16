# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for a e-fuels plant in Africa.
# Unit: fraction / year

Forecast "cost_of_capital_plant_electro_africa" {
	Table = [
		"01-01-2025"	0.231
		"01-01-2030"	0.231
		"01-01-2035"	0.225
		"01-01-2040"	0.212
		"01-01-2045"	0.193
		"01-01-2050"	0.173
	]
	
	Extrapolate = LINEAR
}
