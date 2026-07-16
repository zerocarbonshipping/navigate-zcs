# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Lead time from FID to onstream for biogas-to-biomethanol (SMR) plant.
# Unit: Years

Forecast "lead_time_plant_methanol_bio_smr" {
	Table = [
		"01-01-2030"	3.0
		"01-01-2050"	2.5
	]

	Extrapolate = LINEAR
}
