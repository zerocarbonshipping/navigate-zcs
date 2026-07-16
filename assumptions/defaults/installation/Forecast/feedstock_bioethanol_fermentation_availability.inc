# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global mobilized availability of fermentation feedstock pool
# Unit: dry tons / year

Forecast "feedstock_bioethanol_fermentation_availability" {
	Table = [
		"01-01-2025"	1.403e9
		"01-01-2030"	1.516e9
		"01-01-2040"	1.661e9
		"01-01-2050"	1.812e9
	]

	Extrapolate = LINEAR
}
