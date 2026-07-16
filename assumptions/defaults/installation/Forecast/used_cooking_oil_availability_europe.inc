# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Shipping's availability of used cooking oil in Europe.
# Unit: ton / year

Forecast "used_cooking_oil_availability_europe" {
	Table = [
		"01-01-2025"	12e6
		"01-01-2030"	17e6
		"01-01-2040"	19e6
		"01-01-2050"	20e6
	]
	
	Extrapolate = FLAT
}
