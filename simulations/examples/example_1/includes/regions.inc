# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------------ REGIONS ------------------------------------- 
#
# This file defines the geographic region in which fuel production takes place.
#
# The region plays a role in the upstream (WTT) part of the fuel supply chain, 
# affecting the overall cost and environmental impact of fuel production and delivery.
#
# These regional settings are used to calculate the lifecycle emissions and cost differences 
# for fuels such as bio-methanol, depending on where they are produced and consumed.
#
# ----------------------------------------------------------------------------------

Region "europe" {
	# set region specific source cost
	set_source_opex("grid", Forecast("electricity_cost_europe_mid"))
	
	# set region specific feedstock cost
	set_feedstock_cost("feedstock_biomethanol_gasification", Forecast("feedstock_biomethanol_gasification_cost"))
	
	# set region specific grid emissions
	set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_europe"))
}

Region "*" {
	set_transport_cost("truck", 0.0)
	set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))

	# Bio-methanol
	# The cost (OPEX, CAPEX) as well as emissions can be changed, altering the fuel production cost.
	set_process_capex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_capex"))
	set_process_opex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_opex"))
	set_process_energy("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_energy"))
	set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", <-Variable("carbon_dioxide_per_methanol")>)
}

Import Transport "truck"
