# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Emissions in the electricity grid in Americas.
# Unit: ton emissions / MWh

Forecast "grid_emissions_americas" {
	Table = [
		"01-01-2025"	0.258
		"01-01-2030"	0.176
		"01-01-2035"	0.102
		"01-01-2040"	0.062
		"01-01-2045"	0.045
		"01-01-2050"	0.028
	]
	
	Extrapolate=LINEAR
}
