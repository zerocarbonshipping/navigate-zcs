# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Energy demand of bio-ethanol synthesis (electricity + thermal).
# Unit: MWh / ton fuel / year

Forecast "ethanol_synthesis_bio_energy" {
	Table = [
		"01-01-2030"	1.50
		"01-01-2050"	1.15
	]

	Extrapolate = LINEAR
}
