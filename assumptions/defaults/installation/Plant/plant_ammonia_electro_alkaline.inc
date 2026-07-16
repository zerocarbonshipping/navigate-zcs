# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_ammonia_electro_alkaline" {
	Fuel = Fuel("ammonia_electro")
	Process = Process("ammonia_synthesis_electro_alkaline")

	Capacity = Forecast("ammonia_electro_plant_capacity_mid")

	LeadTime = Forecast("lead_time_plant_electro")
	Lifetime = Forecast("lifetime_plant_ammonia")
	Uptime = Forecast("uptime_plant_electro")
}