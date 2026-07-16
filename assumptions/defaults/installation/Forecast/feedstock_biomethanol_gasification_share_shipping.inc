# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Shipping's share of global available forest residues.
# Unit: fraction

Forecast "feedstock_biomethanol_gasification_share_shipping" {
	Table = [
		"01-01-2025"	0.07
		"01-01-2050"	0.07
	]

	Extrapolate = FLAT
}
