# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-diesel production plant (high).
# Unit: ton / day

Forecast "diesel_electro_plant_capacity_high" {
	Table = [
		"01-01-2025"	19
		"01-01-2026"	149
		"01-01-2027"	280
		"01-01-2028"	411
		"01-01-2050"	411
	]

	Extrapolate = FLAT
}
