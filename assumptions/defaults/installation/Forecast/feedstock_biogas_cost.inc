# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Delivered biomass cost for biogas production (purchase + transport).
# Unit: USD / dry ton

Forecast "feedstock_biogas_cost" {
	Table = [
		"01-01-2025"	 50.
		"01-01-2050"	 50.
	]

	Extrapolate = LINEAR
}
