# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------------ REGIONS ------------------------------------- 
#
# This file defines the geographic area of ammonia production, Europe. 
#
# The specific region plays a role in the upstream (WTT) part of the fuel supply chain, 
# affecting the overall cost and environmental impact of fuel production and delivery.
#
# These regional settings are used to calculate the lifecycle emissions and cost differences 
# for fuels, depending on where they are produced and consumed.
#
# ----------------------------------------------------------------------------------

Region "europe" {

    # set feedstock cost
    set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))

    # set energy source cost and emissions
    set_source_opex("renewable", Forecast("electricity_cost_europe_mid"))

	# e-hydrogen (alkaline)
	set_process_capex("electrolysis_stack_alkaline", Timetable("electrolysis_stack_alkaline_capex"))
	set_process_opex("electrolysis_stack_alkaline", Timetable("electrolysis_stack_alkaline_opex"))
	set_process_energy("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_energy"))
	set_process_lifetime("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_lifetime"))
	set_process_replacement("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_replacement"))

	set_process_capex("hydrogen_electro_alkaline", Timetable("hydrogen_electro_alkaline_capex"))
	set_process_opex("hydrogen_electro_alkaline", Timetable("hydrogen_electro_alkaline_opex"))
	set_process_energy("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_energy"))
	set_process_lifetime("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_lifetime"))
	set_process_replacement("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_replacement"))

	# e-ammonia
	set_process_capex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_capex"))
	set_process_opex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_opex"))
	set_process_energy("ammonia_synthesis_electro_*", Forecast("ammonia_synthesis_energy"))
}
