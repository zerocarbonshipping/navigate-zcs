# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Shipping's share of global engineering, procurement, and construction capacity for electro- and blue fuels.
# Unit: fraction

Forecast "epc_global_share_shipping" {
	Table = [
		"01-01-2025"	0.5
		"01-01-2050"	0.5
	]
	
	Extrapolate = LINEAR
}
