# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "ethanol_synthesis_bio" {
	Feeds = [Feedstock("feedstock_bioethanol_fermentation")]
	Conversions = [Forecast("ethanol_feedstock_fermentation_conversion")]
}
