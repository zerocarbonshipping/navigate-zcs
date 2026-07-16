# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global default cost of fermentation feedstock pool (mid-case).
# Unit: USD / dry ton

Forecast "feedstock_bioethanol_fermentation_cost" {
	Table = [
		"01-01-2025"	 60.
		"01-01-2050"	 60.
	]

	Extrapolate = LINEAR
}
