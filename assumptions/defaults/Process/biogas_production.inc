# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "biogas_production" {
	Feeds = [Feedstock("feedstock_biogas")]
	Conversions = [Variable("biogas_biomass_conversion")]
}
