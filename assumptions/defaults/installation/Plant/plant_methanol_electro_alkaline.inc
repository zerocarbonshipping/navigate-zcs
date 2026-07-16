# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_methanol_electro_alkaline" {
	Fuel = Fuel("methanol_electro")
	Process = Process("methanol_synthesis_electro_alkaline")

	Capacity = Forecast("methanol_electro_plant_capacity_mid")

	LeadTime = Forecast("lead_time_plant_electro")
	Lifetime = Forecast("lifetime_plant_methanol_electro")
	Uptime = Forecast("uptime_plant_electro")
}