# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global default cost of gasification feedstock pool (mid-case).
# Unit: USD / dry ton

Forecast "feedstock_biomethanol_gasification_cost" {
	Table = [
		"01-01-2025"	 65.
		"01-01-2050"	 65.
	]

	Extrapolate = LINEAR
}
