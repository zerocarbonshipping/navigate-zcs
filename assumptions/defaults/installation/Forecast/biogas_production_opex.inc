# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: AD plant OPEX.
# Unit: USD / ton biogas / yr

Forecast "biogas_production_opex" {
	Table = [
		"01-01-2025"	155
		"01-01-2050"	155
	]

	Extrapolate = LINEAR
}
