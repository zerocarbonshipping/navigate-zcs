# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Forecast "trade_growth_container_4500_teu" {
	Table = [
		"01-01-2025"	0.0219
		"01-01-2030"	0.0197
		"01-01-2035"	0.0198
		"01-01-2040"	0.0161
		"01-01-2045"	0.0173
	]

	Interpolate = PREVIOUS # this works as a stepwise interpolation
	Extrapolate = FLAT
}
