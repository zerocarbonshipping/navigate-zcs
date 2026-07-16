# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ PRODUCER ----------------------------------------------
#
# This block defines the FAME producer entity responsible for fuel supply. It is located
# in Europe. It links to a dedicated plant and is subject to regional feedstock constraints, 
# which limit production scale and growth potential.
#
# -------------------------------------------------------------------------------------

Producer "producer_fame" {
	Plants = [Plant("plant_fatty_acid_methyl_ester")]

	MaximumDevelopment = 1

	set_feed_constraint("used_cooking_oil", Forecast("used_cooking_oil_constraint"))
}

# This forecast is simply for a single European producer instead of on a global scale. 
# These numbers can be changed if a lower/higher availability is expected.
Forecast "used_cooking_oil_constraint" {
    Table = [
		"01-01-2025"    2.80e4
        "01-01-2030"    3.30e4
        "01-01-2035"    3.70e4
        "01-01-2040"    3.90e4
        "01-01-2045"    4.10e4
        "01-01-2050"    4.20e4
    ]

	Extrapolate = LINEAR
}