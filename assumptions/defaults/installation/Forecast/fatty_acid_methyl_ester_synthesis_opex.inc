# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of a fatty acid methyl ester synthesis process.
# Unit: USD / ton fuel / year

Forecast "fatty_acid_methyl_ester_synthesis_opex" {
	Table = [
		"01-01-2025"	300
		"01-01-2050"	300
	]
	
	Extrapolate = LINEAR
}
