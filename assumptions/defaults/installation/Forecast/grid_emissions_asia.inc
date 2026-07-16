# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Emissions in the electricity grid in Asia.
# Unit: ton emissions / MWh

Forecast "grid_emissions_asia" {
	Table = [
		"01-01-2025"	0.496
		"01-01-2030"	0.337
		"01-01-2035"	0.195
		"01-01-2040"	0.118
		"01-01-2045"	0.086
		"01-01-2050"	0.053
	]
	
	Extrapolate=LINEAR
}
