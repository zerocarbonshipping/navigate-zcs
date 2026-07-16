# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------------ REGIONS ------------------------------------- 
#
# This file defines the geographic area of FAME production, Europe. 
#
# The specific region plays a role in the upstream (WTT) part of the fuel supply chain, 
# affecting the overall cost and environmental impact of fuel production and delivery.
#
# These regional settings are used to calculate the lifecycle emissions and cost differences 
# for fuels such as FAME, depending on where they are produced and consumed.
#
# ----------------------------------------------------------------------------------

Region "europe" {
    # set region specific source cost
    set_source_opex("grid", Forecast("electricity_cost_europe_mid"))    # renewable LCoE is used as a proxy as no alternative assumption is available

	# set region specific grid emissions
	set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_europe"))
}

Region "*" {

	set_transport_cost("truck", 0.0)
	set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))

	# Feedstock cost and WTT for FAME production
	set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))
	set_feedstock_cost("used_cooking_oil", Forecast("used_cooking_oil_cost_europe"))

	# Cost and emissions of the FAME synthesis
	set_process_capex("fatty_acid_methyl_ester_synthesis", Forecast("fatty_acid_methyl_ester_synthesis_capex"))
	set_process_opex("fatty_acid_methyl_ester_synthesis", Forecast("fatty_acid_methyl_ester_synthesis_opex"))
	set_process_energy("fatty_acid_methyl_ester_synthesis", Forecast("fatty_acid_methyl_ester_synthesis_energy"))
	set_process_wtt("fatty_acid_methyl_ester_synthesis", "carbon_dioxide", <-Variable("carbon_dioxide_per_fame") + Forecast("fame_wtt_carbon_dioxide")>)
	set_process_wtt("fatty_acid_methyl_ester_synthesis", "methane", Forecast("fame_wtt_methane"))
	set_process_wtt("fatty_acid_methyl_ester_synthesis", "nitrous_oxide", Forecast("fame_wtt_nitrous_oxide"))
}

Transport "truck" {
}
