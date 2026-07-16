# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_methanol_bio_gasification" {
	Fuel = Fuel("methanol_bio")
	Process = Process("methanol_synthesis_bio_gasification")

	Capacity = Forecast("methanol_bio_gasification_plant_capacity")

	LeadTime = Forecast("lead_time_plant_bio")
	Lifetime = Forecast("lifetime_plant_methanol_bio_gasification")
	Uptime = Forecast("uptime_plant_bio")

	set_feed_transport("feedstock_biomethanol_gasification", Transport("truck"))
	set_feed_distance("feedstock_biomethanol_gasification", Forecast("distance_feedstock_biomethanol_gasification_to_methanol_plant"))
}
