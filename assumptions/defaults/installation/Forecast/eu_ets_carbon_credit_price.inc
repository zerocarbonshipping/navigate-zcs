# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Price of carbon credits under the EU ETS regulation.
# Unit: USD / ton

Forecast "eu_ets_carbon_credit_price" {
	Table = [
		"01-01-2024"	100
		"01-01-2025"	119
		"01-01-2030"	155
		"01-01-2035"	198
		"01-01-2040"	252
		"01-01-2045"	325
		"01-01-2050"	417
	]
	
	Extrapolate = LINEAR
}
