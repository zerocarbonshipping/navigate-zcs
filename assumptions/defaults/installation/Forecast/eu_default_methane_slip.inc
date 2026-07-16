# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Average methane slip under EU ETS and FuelEU Maritime assuming all DF-methane vessels in 2025 have LNG Otto (dual fuel slow speed) and will in 2050 have LNG Diesel (dual fuels).
# Unit: Ton emission / ton fuel

Forecast "eu_default_methane_slip" {
	Table = [
		"01-01-2025"	0.017
		"01-01-2050"	0.002
	]
	
	Extrapolate = FLAT
}
