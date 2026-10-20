# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_diesel_electro_soec" {
	Fuel = Fuel("diesel_electro")
	Process = Process("diesel_synthesis_electro_soec")

    Capacity = Forecast("diesel_electro_plant_capacity_mid")

    LeadTime = Forecast("lead_time_plant_electro")
    Lifetime = Forecast("lifetime_plant_diesel")
    Uptime = Forecast("uptime_plant_electro")
}