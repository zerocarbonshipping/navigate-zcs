# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of a bio-methanol production plant.
# Unit: ton / day

Forecast "methanol_bio_gasification_plant_capacity" {
	Table = [
		"01-01-2030"	1500
		"01-01-2050"	1500
	]
	
	Extrapolate=LINEAR
}
