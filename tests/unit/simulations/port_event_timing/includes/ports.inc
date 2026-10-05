# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Two liquid-market oil fuels with identical heating value, density and
# emissions, so per ton and per GJ the cheaper one is cheaper outright. Prices
# and WTT are set on every port the vessel's route calls at.
Import Port "port_global"
Import Port "port_europe"

Fuel "oil_cheap" {
	FuelType = OIL
	LiquidMarket = TRUE

	LowerHeatingValue = 40
	MassDensity = 0.9

	set_ttw("carbon_dioxide", 3.1)
}

Fuel "oil_dear" {
	FuelType = OIL
	LiquidMarket = TRUE

	LowerHeatingValue = 40
	MassDensity = 0.9

	set_ttw("carbon_dioxide", 3.1)
}

Port "*" {
	set_bunker_price_overwrite("oil_cheap", 500)                   # USD/ton
	set_bunker_price_overwrite("oil_dear", 600)                    # USD/ton

	set_bunker_wtt_overwrite("oil_cheap", "carbon_dioxide", 0.6)   # ton/ton fuel
	set_bunker_wtt_overwrite("oil_dear", "carbon_dioxide", 0.6)
}
