# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Emissions in the electricity grid in Europe.
# Unit: ton emissions / MWh

Forecast "grid_emissions_europe" {
	Table = [
		"01-01-2025"	0.245
		"01-01-2030"	0.166
		"01-01-2035"	0.096
		"01-01-2040"	0.058
		"01-01-2045"	0.042
		"01-01-2050"	0.026
	]
	
	Extrapolate=LINEAR
}
