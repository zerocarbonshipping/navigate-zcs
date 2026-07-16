# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of a blue ammonia production plant.
# Unit: ton / day

Forecast "ammonia_blue_plant_capacity" {
	Table = [
		"01-01-2025"	4110
		"01-01-2050"	4110
	]

	Extrapolate = FLAT
}
