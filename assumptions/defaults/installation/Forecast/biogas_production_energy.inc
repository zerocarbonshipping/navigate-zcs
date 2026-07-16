# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: AD plant electricity consumption.
# Unit: MWh / ton biogas

Forecast "biogas_production_energy" {
	Table = [
		"01-01-2025"	0.15
		"01-01-2050"	0.15
	]

	Extrapolate = LINEAR
}
