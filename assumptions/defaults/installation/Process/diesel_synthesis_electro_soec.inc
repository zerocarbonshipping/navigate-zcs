# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "diesel_synthesis_electro_soec" {
	Feeds = [Process("hydrogen_electro_soec_compression_25_bar"), Feedstock("carbon_dioxide_biogenic")]
	Conversions = [Variable("diesel_hydrogen_conversion"), Variable("diesel_carbon_dioxide_conversion")]
}
