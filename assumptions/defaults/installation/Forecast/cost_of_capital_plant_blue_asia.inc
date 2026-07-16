# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for a blue-fuels plant in Asia.
# Unit: fraction / year

Forecast "cost_of_capital_plant_blue_asia" {
	Table = [
		"01-01-2025"	0.096
		"01-01-2050"	0.067
	]
	
	Extrapolate = LINEAR
}
