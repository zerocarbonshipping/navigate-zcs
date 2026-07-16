# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of an e-methanol production plant (high).
# Unit: ton / day

Forecast "methanol_electro_plant_capacity_high" {
	Table = [
		"01-01-2025"	188
		"01-01-2026"	1495
		"01-01-2027"	2802
		"01-01-2028"	4110
		"01-01-2050"	4110
	]

	Extrapolate = FLAT
}
