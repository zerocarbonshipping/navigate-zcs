# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Emissions in the electricity grid in the Middle East.
# Unit: ton emissions / MWh

Forecast "grid_emissions_middle_east" {
	Table = [
		"01-01-2025"	0.554
		"01-01-2030"	0.376
		"01-01-2035"	0.218
		"01-01-2040"	0.132
		"01-01-2045"	0.096
		"01-01-2050"	0.059
	]
	
	Extrapolate=LINEAR
}
