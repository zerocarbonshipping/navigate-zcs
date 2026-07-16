# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "fatty_acid_methyl_ester_synthesis" {
	Feeds = [Feedstock("used_cooking_oil"), Feedstock("methanol_grey"), Feedstock("demineralized_water")]
	Conversions = [Variable("fame_used_cooking_oil_conversion"), Variable("fame_grey_methanol_conversion"), Variable("fame_demineralized_water_conversion")]
}
