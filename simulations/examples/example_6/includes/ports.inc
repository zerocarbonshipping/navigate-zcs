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

	# FAME and e-fuel prices and upstream emissions from placeholders.inc: replace
	# them there with your source's.
	set_bunker_price_overwrite("fatty_acid_methyl_ester", Forecast("rhine_fame_price"))
	set_bunker_wtt_overwrite("fatty_acid_methyl_ester", "carbon_dioxide", Forecast("rhine_fame_wtt_carbon_dioxide"))
	set_bunker_wtt_overwrite("fatty_acid_methyl_ester", "methane", Variable("rhine_fame_wtt_methane"))
	set_bunker_price_overwrite("diesel_electro", Forecast("rhine_e_diesel_price"))
	set_bunker_wtt_overwrite("diesel_electro", "carbon_dioxide", Variable("rhine_e_diesel_wtt_carbon_dioxide"))
	set_bunker_price_overwrite("methanol_electro", Forecast("rhine_e_methanol_price"))
	set_bunker_wtt_overwrite("methanol_electro", "carbon_dioxide", Variable("rhine_e_methanol_wtt_carbon_dioxide"))

	# Handling: storage and the bunkering service, per ton, on top of the price
	# (INVENTED, in placeholders.inc).
	set_handling_cost("fossil_fuel_oil", Variable("rhine_handling_fuel_oil"))
	set_handling_cost("liquefied_natural_gas", Variable("rhine_handling_lng"))
	set_handling_cost("fatty_acid_methyl_ester", Variable("rhine_handling_fame"))
	set_handling_cost("diesel_electro", Variable("rhine_handling_e_diesel"))
	set_handling_cost("methanol_electro", Variable("rhine_handling_e_methanol"))
}
