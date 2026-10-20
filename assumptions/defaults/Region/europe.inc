# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Region "europe" {

    # feedstock --------------------------------------------------------------------------------------------------------
	# feedstock cost
    set_feedstock_cost("used_cooking_oil", Forecast("used_cooking_oil_cost_europe"))

    # sources ----------------------------------------------------------------------------------------------------------
    # source cost
    set_source_opex("renewable", Forecast("electricity_cost_europe_mid"))
    set_source_opex("grid", Forecast("electricity_cost_europe_mid"))

	# source emissions
	set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_europe"))

    # processes --------------------------------------------------------------------------------------------------------
	# fatty acid methyl ester (FAME)
	set_process_capex("fatty_acid_methyl_ester_synthesis", Forecast("fatty_acid_methyl_ester_synthesis_capex"))
	set_process_opex("fatty_acid_methyl_ester_synthesis", Forecast("fatty_acid_methyl_ester_synthesis_opex"))
	set_process_energy("fatty_acid_methyl_ester_synthesis", Forecast("fatty_acid_methyl_ester_synthesis_energy"))
	set_process_wtt("fatty_acid_methyl_ester_synthesis", "carbon_dioxide", <-Variable("carbon_dioxide_per_fame") + Forecast("fame_wtt_carbon_dioxide")>)
	set_process_wtt("fatty_acid_methyl_ester_synthesis", "methane", Forecast("fame_wtt_methane"))
	set_process_wtt("fatty_acid_methyl_ester_synthesis", "nitrous_oxide", Forecast("fame_wtt_nitrous_oxide"))
}
