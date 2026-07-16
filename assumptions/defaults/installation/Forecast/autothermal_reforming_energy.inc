# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Energy demand of a autothermal reforming process.
# Unit: USD / MWh

Forecast "autothermal_reforming_energy" {
	Table = [
		"01-01-2025"	3.495
		"01-01-2050"	3.495
	]
	
	Extrapolate = LINEAR
}
