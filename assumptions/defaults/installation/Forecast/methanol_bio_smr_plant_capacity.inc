# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capacity of a biogas-to-biomethanol (SMR) production plant.
# Unit: ton / day

Forecast "methanol_bio_smr_plant_capacity" {
	Table = [
		"01-01-2030"	198
		"01-01-2050"	342
	]

	Extrapolate = LINEAR
}
