# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# All fuel-side prices and emissions pinned as explicit constants so upstream
# assumption changes cannot silently re-size the scenario. The oil WTT factor
# is what the WTW levy prices; e-ammonia is emission-free on both legs, so
# the levy prices exactly one fuel.
Import Port "port_global"
Import Port "port_europe"

Port "*" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("ammonia_electro", TRUE)

	set_bunker_price_overwrite("fossil_fuel_oil", 485)                    # USD/ton
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", 0.68)   # ton/ton fuel

	# e-ammonia: renewable production, no upstream emissions
	set_bunker_wtt_overwrite("ammonia_electro", "carbon_dioxide", 0.)
}
