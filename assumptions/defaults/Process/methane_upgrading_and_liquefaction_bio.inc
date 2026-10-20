# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "methane_upgrading_and_liquefaction_bio" {
	Feeds = [Process("biogas_production")]
	Conversions = [Variable("methane_biogas_to_lbm_conversion")]
}
