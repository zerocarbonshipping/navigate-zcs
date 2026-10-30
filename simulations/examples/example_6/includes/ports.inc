# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PORTS - what is sold where. Fuel oil at every port; LNG, FAME, e-diesel and
# e-methanol at Duisburg and Mannheim only. The fuels imported only so that the
# copied regulation parses are bunkerable nowhere.

Port "duisburg" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", TRUE)
	set_bunkering_allowed("fatty_acid_methyl_ester", TRUE)
	set_bunkering_allowed("diesel_electro", TRUE)
	set_bunkering_allowed("methanol_electro", TRUE)
}

Port "mannheim" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", TRUE)
	set_bunkering_allowed("fatty_acid_methyl_ester", TRUE)
	set_bunkering_allowed("diesel_electro", TRUE)
	set_bunkering_allowed("methanol_electro", TRUE)
}

Port "cologne" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", FALSE)
	set_bunkering_allowed("fatty_acid_methyl_ester", FALSE)
	set_bunkering_allowed("diesel_electro", FALSE)
	set_bunkering_allowed("methanol_electro", FALSE)
}

Port "koblenz" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", FALSE)
	set_bunkering_allowed("fatty_acid_methyl_ester", FALSE)
	set_bunkering_allowed("diesel_electro", FALSE)
	set_bunkering_allowed("methanol_electro", FALSE)
}

Port "mainz" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", FALSE)
	set_bunkering_allowed("fatty_acid_methyl_ester", FALSE)
	set_bunkering_allowed("diesel_electro", FALSE)
	set_bunkering_allowed("methanol_electro", FALSE)
}

Port "*" {
	set_bunkering_allowed("methanol_bio", FALSE)
	set_bunkering_allowed("methane_bio", FALSE)
	set_bunkering_allowed("methane_electro", FALSE)
	set_bunkering_allowed("ammonia_blue", FALSE)
	set_bunkering_allowed("ammonia_electro", FALSE)

	# Fossil prices and upstream emissions at the library's values (as DefaultPort).
	set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))
	set_bunker_price_overwrite("liquefied_natural_gas", Forecast("liquefied_natural_gas_price_global"))
	set_bunker_wtt_overwrite("liquefied_natural_gas", "carbon_dioxide", Forecast("liquefied_natural_gas_wtt_carbon_dioxide"))
	set_bunker_wtt_overwrite("liquefied_natural_gas", "methane", Forecast("liquefied_natural_gas_wtt_methane"))
}
