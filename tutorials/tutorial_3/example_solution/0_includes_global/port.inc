# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of port
Port "port" {
	set_bunker_price_overwrite("heavy_fuel_oil", 250)
	set_bunker_wtt_overwrite("heavy_fuel_oil", "carbon_dioxide", 0.62)
}