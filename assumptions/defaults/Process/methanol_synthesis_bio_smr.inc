# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "methanol_synthesis_bio_smr" {
	Feeds = [Process("biogas_production")]
	Conversions = [Variable("methanol_feedstock_biogas_smr_conversion")]
}
