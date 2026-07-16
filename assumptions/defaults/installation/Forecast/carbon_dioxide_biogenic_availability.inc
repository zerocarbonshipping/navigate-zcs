# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global availability of biogenic carbon feedstock.
# Unit: ton / year

Forecast "carbon_dioxide_biogenic_availability" {
	Table = [
		"01-01-2024"	70e6
		"01-01-2050"	350e6
	]
	
	Extrapolate=LINEAR
}
