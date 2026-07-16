# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Forecast of the global natural gas feedstock price.
# Unit: USD / ton feedstock / year

Forecast "natural_gas_price_global" {
	Table = [
		"01-01-2026"	200
		"01-01-2050"	200
	]

	Extrapolate = FLAT
}
