# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_methanol_bio_smr" {
	Fuel = Fuel("methanol_bio")
	Process = Process("methanol_synthesis_bio_smr")

	Capacity = Forecast("methanol_bio_smr_plant_capacity")

	LeadTime = Forecast("lead_time_plant_methanol_bio_smr")
	Lifetime = Forecast("lifetime_plant_methanol_bio_smr")
	Uptime = Forecast("uptime_plant_methanol_bio_smr")

	set_feed_transport("feedstock_biogas", Transport("truck"))
	set_feed_distance("feedstock_biogas", Forecast("distance_feedstock_biogas_to_methane_plant"))
}
