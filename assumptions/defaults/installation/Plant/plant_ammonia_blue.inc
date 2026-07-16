# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plant "plant_ammonia_blue" {
	Fuel = Fuel("ammonia_blue")
	Process = Process("ammonia_synthesis_blue")

	Capacity = Forecast("ammonia_blue_plant_capacity")

    LeadTime = Forecast("lead_time_plant_blue")
    Lifetime = Forecast("lifetime_plant_ammonia")
    Uptime = Forecast("uptime_plant_blue")
}
