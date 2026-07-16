# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of transporting and storing carbon dioxide.
# Unit: USD / ton CO2

Forecast "carbon_transport_storage_cost" {
	Table = [
		"01-01-2025"	27.3
		"01-01-2050"	27.3
	]
	
	Extrapolate = LINEAR
}
