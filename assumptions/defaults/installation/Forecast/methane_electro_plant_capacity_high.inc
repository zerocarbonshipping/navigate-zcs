# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of a methane production plant (high).
# Unit: ton / day

Forecast "methane_electro_plant_capacity_high" {
	Table = [
		"01-01-2025"	94
		"01-01-2026"	747
		"01-01-2027"	1401
		"01-01-2028"	2055
		"01-01-2050"	2055
	]

	Extrapolate = FLAT
}
