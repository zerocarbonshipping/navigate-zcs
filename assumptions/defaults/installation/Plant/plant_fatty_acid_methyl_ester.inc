# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_fatty_acid_methyl_ester" {
	Fuel = Fuel("fatty_acid_methyl_ester")
	Process = Process("fatty_acid_methyl_ester_synthesis")

	Capacity = Forecast("fatty_acid_methyl_ester_synthesis_plant_capacity")

	LeadTime = Forecast("lead_time_plant_fame")
	Lifetime = Forecast("lifetime_plant_fame")
	Uptime = Forecast("uptime_plant_bio")
}
