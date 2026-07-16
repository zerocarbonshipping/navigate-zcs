# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Conversion rate of fermentation feedstock pool to ethanol.
# Unit: dry ton feedstock / ton fuel

Forecast "ethanol_feedstock_fermentation_conversion" {
	Table = [
		"01-01-2030"  3.8
		"01-01-2050"  3.6
	]

	Extrapolate = LINEAR
}
