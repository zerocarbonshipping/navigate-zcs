# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Emissions in the electricity grid in Africa.
# Unit: ton emissions / MWh

Forecast "grid_emissions_africa" {
	Table = [
		"01-01-2025"	0.469
		"01-01-2030"	0.319
		"01-01-2035"	0.185
		"01-01-2040"	0.112
		"01-01-2045"	0.075
		"01-01-2050"	0.050
	]
	
	Extrapolate=LINEAR
}
