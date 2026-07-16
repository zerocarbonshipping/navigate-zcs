# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global mobilized availability of gasification feedstock pool
# Unit: dry tons / year

Forecast "feedstock_biomethanol_gasification_availability" {
	Table = [
		"01-01-2025"	1.139e9
		"01-01-2030"	1.206e9
		"01-01-2040"	1.285e9
		"01-01-2050"	1.361e9
	]

	Extrapolate = LINEAR
}
