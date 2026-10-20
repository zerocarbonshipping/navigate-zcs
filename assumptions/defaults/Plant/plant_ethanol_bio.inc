# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_ethanol_bio" {
	Fuel = Fuel("ethanol_bio")
	Process = Process("ethanol_synthesis_bio")

	Capacity = Forecast("ethanol_bio_plant_capacity")

	LeadTime = Forecast("lead_time_plant_bio")
	Lifetime = Forecast("lifetime_plant_ethanol_bio")
	Uptime = Forecast("uptime_plant_bio")

	set_feed_transport("feedstock_bioethanol_fermentation", Transport("truck"))
	set_feed_distance("feedstock_bioethanol_fermentation", Forecast("distance_feedstock_bioethanol_fermentation_to_ethanol_plant"))
}
