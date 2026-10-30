# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# REGIONS - Europe, where all the fuels are made. Import Region brings Europe's own
# lines (power prices, grid emissions, used cooking oil cost, FAME process). The
# lines for the other processes and feedstocks are restated below from the Region "*"
# block of assumptions/modules/installation/default_region.inc.

Import Region "europe"

Region "*" {
	# feedstocks
	set_feedstock_cost("carbon_dioxide_biogenic", Forecast("carbon_dioxide_biogenic_cost"))
	set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))
	set_feedstock_cost("methanol_grey", Forecast("methanol_grey_cost"))
	set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", Forecast("carbon_dioxide_biogenic_capture_rate"))
	set_feedstock_wtt("methanol_grey", "carbon_dioxide", Forecast("methanol_grey_wtt"))

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

	# e-methanol
	set_process_capex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_capex"))
	set_process_opex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_opex"))
	set_process_energy("methanol_synthesis_electro_*", Forecast("methanol_synthesis_electro_energy"))
	set_process_wtt("methanol_synthesis_electro_*", "carbon_dioxide", <Variable("methanol_carbon_dioxide_conversion") - Variable("carbon_dioxide_per_methanol")>)

	# e-diesel
	set_process_capex("diesel_synthesis_electro_*", Timetable("diesel_synthesis_electro_capex"))
	set_process_opex("diesel_synthesis_electro_*", Timetable("diesel_synthesis_electro_opex"))
	set_process_energy("diesel_synthesis_electro_*", Forecast("diesel_synthesis_electro_energy"))
	set_process_wtt("diesel_synthesis_electro_*", "carbon_dioxide", <Variable("diesel_carbon_dioxide_conversion") - Variable("carbon_dioxide_per_diesel_electro")>)

	# plant to quayside within a region
	set_transport_cost("truck", 0.0)
	set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))
}

Import Transport "truck"
