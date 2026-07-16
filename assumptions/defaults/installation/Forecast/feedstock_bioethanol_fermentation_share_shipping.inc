# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Shipping's share of global available crop residues.
# Unit: fraction

Forecast "feedstock_bioethanol_fermentation_share_shipping" {
	Table = [
		"01-01-2025"	0.02
		"01-01-2050"	0.02
	]

	Extrapolate = FLAT
}
