# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global mobilized availability of biogas feedstock pool
# Unit: dry tons / year

Forecast "feedstock_biogas_availability" {
	Table = [
		"01-01-2025"	8.22e8
		"01-01-2030"	8.92e8
		"01-01-2040"	9.84e8
		"01-01-2050"	1.081e9
	]

	Extrapolate = LINEAR
}
