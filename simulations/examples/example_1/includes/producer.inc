# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ PRODUCER ----------------------------------------------
#
# This block defines the bio-methanol producer entity responsible for fuel supply
# across European demand centers. It links to a dedicated plant and is subject to
# regional feedstock constraints, which limit production scale and growth potential.
#
# -------------------------------------------------------------------------------------

Producer "producer_methanol_bio" {
	Plants = [Plant("plant_methanol_bio_gasification")]

    MaximumDevelopment = 1

    set_feed_constraint("feedstock_biomethanol_gasification", Forecast("feedstock_biomethanol_gasification_constraint"))
}

# This forecast is simply for a single European producer instead of on a global scale.
# These numbers can be changed if a lower availability is expected.
Forecast "feedstock_biomethanol_gasification_constraint" {
    Table = [
		"01-01-2025"	0.03e6
		"01-01-2030"	0.15e6
		"01-01-2035"	0.90e6
		"01-01-2040"	1.14e6
		"01-01-2045"	1.26e6
		"01-01-2050"	1.38e6
    ]

	Extrapolate = LINEAR
}