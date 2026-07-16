# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Yearly trade-growth for a vessel segment.
# Unit: Fraction / year

Forecast "trade_growth_general_cargo" {
	Table = [
		"01-01-2025"	0.0031
		"01-01-2030"	0.0028
		"01-01-2035"	0.0025
		"01-01-2040"	0.0000
	]

	Interpolate = PREVIOUS # this works as a stepwise interpolation
	Extrapolate = FLAT
}