# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of a bio-ethanol production plant (cellulosic).
# Unit: ton / day

Forecast "ethanol_bio_plant_capacity" {
	Table = [
		"01-01-2030"	230
		"01-01-2050"	400
	]

	Extrapolate = LINEAR
}
