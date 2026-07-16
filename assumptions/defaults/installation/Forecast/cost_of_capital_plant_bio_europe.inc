# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for a bio-fuels plant in Europe.
# Unit: fraction / year

Forecast "cost_of_capital_plant_bio_europe" {
	Table = [
		"01-01-2025"	0.074
		"01-01-2050"	0.048
	]
	
	Extrapolate = LINEAR
}
