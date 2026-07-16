# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "methanol_synthesis_bio_gasification" {
	Feeds = [Feedstock("feedstock_biomethanol_gasification")]
	Conversions = [Variable("methanol_feedstock_gasification_conversion")]
}
