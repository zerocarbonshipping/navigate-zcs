# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: AD plant CAPEX.
# Unit: USD / ton biogas annual capacity

Forecast "biogas_production_capex" {
	Table = [
		"01-01-2025"	950
		"01-01-2050"	950
	]

	Extrapolate = LINEAR
}
