# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_methane_electro_soec" {
	Fuel = Fuel("methane_electro")
	Process = Process("methane_liquefaction_electro_soec")

	Capacity = Forecast("methane_electro_plant_capacity_mid")

	LeadTime = Forecast("lead_time_plant_electro")
	Lifetime = Forecast("lifetime_plant_methane")
	Uptime = Forecast("uptime_plant_electro")
}