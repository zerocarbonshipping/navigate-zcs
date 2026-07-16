# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: The emissions associated with transport via truck.
# Unit: ton emission / ton-nautical mile

Forecast "truck_emissions" {
	Table = [
		"01-01-2025"	443.4
		"01-01-2030"	426.4
		"01-01-2035"	394.6
		"01-01-2040"	349.3
		"01-01-2045"	301.7
		"01-01-2050"	254.0
	]
	
	Multiplier = 1e-6	# conversion from gCO2eq to tCOeq
	Extrapolate = LINEAR
}
