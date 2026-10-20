# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "methanol_synthesis_electro_soec" {
	Feeds = [Process("hydrogen_electro_soec_compression_10_bar"), Feedstock("carbon_dioxide_biogenic")]
	Conversions = [Variable("methanol_hydrogen_conversion"), Variable("methanol_carbon_dioxide_conversion")]
}
