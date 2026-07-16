# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_methane_bio" {
	Fuel = Fuel("methane_bio")
	Process = Process("methane_upgrading_and_liquefaction_bio")

	Capacity = Forecast("methane_bio_plant_capacity")

	LeadTime = Forecast("lead_time_plant_bio")
	Lifetime = Forecast("lifetime_plant_methane")
	Uptime = Forecast("uptime_plant_bio")

	set_feed_transport("feedstock_biogas", Transport("truck"))
	set_feed_distance("feedstock_biogas", Forecast("distance_feedstock_biogas_to_methane_plant"))
}
