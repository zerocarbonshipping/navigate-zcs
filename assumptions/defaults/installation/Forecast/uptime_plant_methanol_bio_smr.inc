# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Uptime fraction for biogas-to-biomethanol (SMR) plant.
# Unit: fraction (0-1)

Forecast "uptime_plant_methanol_bio_smr" {
	Table = [
		"01-01-2030"	0.90
		"01-01-2050"	0.95
	]

	Extrapolate = LINEAR
}
