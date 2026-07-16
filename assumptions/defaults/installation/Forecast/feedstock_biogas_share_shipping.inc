# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Shipping's share of global available biogas pathway biomass.
# Unit: fraction

Forecast "feedstock_biogas_share_shipping" {
	Table = [
		"01-01-2025"	0.25
		"01-01-2050"	0.25
	]

	Extrapolate = FLAT
}
