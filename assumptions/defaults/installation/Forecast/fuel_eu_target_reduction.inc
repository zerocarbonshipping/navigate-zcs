# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: The GFI targets of the FuelEU Maritime regulation.
# Unit: gCO2eq/MJ

Forecast "fuel_eu_target_reduction" {
	Table = [
		"01-01-2022"	1.0
		"01-01-2025"	0.98
		"01-01-2030"	0.94
		"01-01-2035"	0.855
		"01-01-2040"	0.69
		"01-01-2045"	0.38
		"01-01-2050"	0.20
	]
	
	Multiplier = 91.16		# baseline value from FuelEU
	Extrapolate = FLAT
	Interpolate = PREVIOUS
}
