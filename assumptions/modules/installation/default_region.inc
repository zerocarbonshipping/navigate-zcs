# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Import Region "africa"
Import Region "americas"
Import Region "asia"
Import Region "europe"
Import Region "middle_east"

Region "*" {

    # feedstock --------------------------------------------------------------------------------------------------------

    # feedstock cost
	set_feedstock_cost("natural_gas", Forecast("natural_gas_price_global"))
	set_feedstock_cost("carbon_dioxide_biogenic", Forecast("carbon_dioxide_biogenic_cost"))
    set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))
	set_feedstock_cost("methanol_grey", Forecast("methanol_grey_cost"))
	set_feedstock_cost("feedstock_biogas", Forecast("feedstock_biogas_cost"))
	set_feedstock_cost("feedstock_biomethanol_gasification", Forecast("feedstock_biomethanol_gasification_cost"))
	set_feedstock_cost("feedstock_bioethanol_fermentation", Forecast("feedstock_bioethanol_fermentation_cost"))

    # feedstock emissions
	set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", Forecast("carbon_dioxide_biogenic_capture_rate"))
	set_feedstock_wtt("methanol_grey", "carbon_dioxide", Forecast("methanol_grey_wtt"))
	set_feedstock_wtt("natural_gas", "carbon_dioxide", Forecast("natural_gas_wtt_carbon_dioxide"))
	set_feedstock_wtt("natural_gas", "methane", Forecast("natural_gas_wtt_methane"))
	set_feedstock_wtt("feedstock_biogas", "methane", Forecast("feedstock_biogas_wtt_methane"))

    # transport --------------------------------------------------------------------------------------------------------

	# transport emissions
	set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))

	# hydrogen ---------------------------------------------------------------------------------------------------------

    # blue hydrogen (autothermal reforming)
    set_process_capex("autothermal_reforming", Timetable("autothermal_reforming_capex"))
	set_process_opex("autothermal_reforming", <Timetable("autothermal_reforming_opex") + Forecast("carbon_transport_storage_cost") * Forecast("autothermal_reforming_capture_rate") * Variable("carbon_dioxide_per_hydrogen_blue")>)
	set_process_energy("autothermal_reforming", Forecast("autothermal_reforming_energy"))
    set_process_wtt("autothermal_reforming", "carbon_dioxide", <(1. - Forecast("autothermal_reforming_capture_rate")) * Variable("carbon_dioxide_per_hydrogen_blue")>)

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

	# e-hydrogen (PEM)
	set_process_capex("electrolysis_stack_pem", Timetable("electrolysis_stack_pem_capex"))
	set_process_opex("electrolysis_stack_pem", Timetable("electrolysis_stack_pem_opex"))
	set_process_energy("electrolysis_stack_pem", Forecast("electrolysis_stack_pem_energy"))
	set_process_lifetime("electrolysis_stack_pem", Forecast("electrolysis_stack_pem_lifetime"))
	set_process_replacement("electrolysis_stack_pem", Forecast("electrolysis_stack_pem_replacement"))

	set_process_capex("hydrogen_electro_pem", Timetable("hydrogen_electro_pem_capex"))
	set_process_opex("hydrogen_electro_pem", Timetable("hydrogen_electro_pem_opex"))
	set_process_energy("hydrogen_electro_pem", Forecast("hydrogen_electro_pem_energy"))
	set_process_lifetime("hydrogen_electro_pem", Forecast("hydrogen_electro_pem_lifetime"))
	set_process_replacement("hydrogen_electro_pem", Forecast("hydrogen_electro_pem_replacement"))

	# e-hydrogen (solid oxide)
	set_process_capex("electrolysis_stack_soec", Timetable("electrolysis_stack_soec_capex"))
	set_process_opex("electrolysis_stack_soec", Timetable("electrolysis_stack_soec_opex"))
	set_process_energy("electrolysis_stack_soec", Forecast("electrolysis_stack_soec_energy"))
	set_process_lifetime("electrolysis_stack_soec", Forecast("electrolysis_stack_soec_lifetime"))
	set_process_replacement("electrolysis_stack_soec", Forecast("electrolysis_stack_soec_replacement"))

	set_process_capex("hydrogen_electro_soec", Timetable("hydrogen_electro_soec_capex"))
	set_process_opex("hydrogen_electro_soec", Timetable("hydrogen_electro_soec_opex"))
	set_process_energy("hydrogen_electro_soec", Forecast("hydrogen_electro_soec_energy"))
	set_process_lifetime("hydrogen_electro_soec", Forecast("hydrogen_electro_soec_lifetime"))
	set_process_replacement("hydrogen_electro_soec", Forecast("hydrogen_electro_soec_replacement"))

	# hydrogen compression --------------------------------------------------------------------------------------------

	# compression (0 to 30 bar)
	set_process_capex("hydrogen_electro_soec_compression_30_bar", Timetable("hydrogen_compression_30_bar_capex"))
	set_process_opex("hydrogen_electro_soec_compression_30_bar", Timetable("hydrogen_compression_30_bar_opex"))
	set_process_energy("hydrogen_electro_soec_compression_30_bar", Forecast("hydrogen_compression_30_bar_energy"))
	set_process_lifetime("hydrogen_electro_soec_compression_30_bar", Forecast("hydrogen_compression_lifetime"))
	set_process_replacement("hydrogen_electro_soec_compression_30_bar", Forecast("hydrogen_compression_replacement"))

	# compression (0 to 25 bar)
	set_process_capex("hydrogen_electro_soec_compression_25_bar", Timetable("hydrogen_compression_25_bar_capex"))
	set_process_opex("hydrogen_electro_soec_compression_25_bar", Timetable("hydrogen_compression_25_bar_opex"))
	set_process_energy("hydrogen_electro_soec_compression_25_bar", Forecast("hydrogen_compression_25_bar_energy"))
	set_process_lifetime("hydrogen_electro_soec_compression_25_bar", Forecast("hydrogen_compression_lifetime"))
	set_process_replacement("hydrogen_electro_soec_compression_25_bar", Forecast("hydrogen_compression_replacement"))

	# compression (0 to 10 bar)
	set_process_capex("hydrogen_electro_soec_compression_10_bar", Timetable("hydrogen_compression_10_bar_capex"))
	set_process_opex("hydrogen_electro_soec_compression_10_bar", Timetable("hydrogen_compression_10_bar_opex"))
	set_process_energy("hydrogen_electro_soec_compression_10_bar", Forecast("hydrogen_compression_10_bar_energy"))
	set_process_lifetime("hydrogen_electro_soec_compression_10_bar", Forecast("hydrogen_compression_lifetime"))
	set_process_replacement("hydrogen_electro_soec_compression_10_bar", Forecast("hydrogen_compression_replacement"))

	# ammonia ----------------------------------------------------------------------------------------------------------

	# blue ammonia
	set_process_capex("ammonia_synthesis_blue", Timetable("ammonia_synthesis_capex"))
	set_process_opex("ammonia_synthesis_blue", Timetable("ammonia_synthesis_opex"))
	set_process_energy("ammonia_synthesis_blue", Forecast("ammonia_synthesis_energy"))

	# e-ammonia
	set_process_capex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_capex"))
	set_process_opex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_opex"))
	set_process_energy("ammonia_synthesis_electro_*", Forecast("ammonia_synthesis_energy"))

    # methane ----------------------------------------------------------------------------------------------------------

	# biogas production (anaerobic digestion)
	set_process_capex("biogas_production", Forecast("biogas_production_capex"))
	set_process_opex("biogas_production", Forecast("biogas_production_opex"))
	set_process_energy("biogas_production", Forecast("biogas_production_energy"))

	# bio-methane (upgrading + liquefaction)
	set_process_capex("methane_upgrading_and_liquefaction_bio", Forecast("methane_upgrading_and_liquefaction_bio_capex"))
	set_process_opex("methane_upgrading_and_liquefaction_bio", Forecast("methane_upgrading_and_liquefaction_bio_opex"))
	set_process_energy("methane_upgrading_and_liquefaction_bio", Forecast("methane_upgrading_and_liquefaction_bio_energy"))
	set_process_wtt("methane_upgrading_and_liquefaction_bio", "carbon_dioxide", <-Variable("carbon_dioxide_per_methane") - Variable("methane_bio_fertilizer_displacement_credit")>)
	set_process_wtt("methane_upgrading_and_liquefaction_bio", "methane", Forecast("methane_synthesis_and_liquefaction_wtt_methane"))

	# e-methane
	set_process_capex("methane_synthesis_electro_*", Timetable("methane_synthesis_electro_capex"))
	set_process_opex("methane_synthesis_electro_*", Timetable("methane_synthesis_electro_opex"))
	set_process_energy("methane_synthesis_electro_*", Forecast("methane_synthesis_electro_energy"))

	# e-methane liquefaction
	set_process_capex("methane_liquefaction_*", Timetable("methane_liquefaction_capex"))
	set_process_opex("methane_liquefaction_*", Timetable("methane_liquefaction_opex"))
	set_process_energy("methane_liquefaction_*", Forecast("methane_liquefaction_energy"))

	# methanol ----------------------------------------------------------------------------------------------------------

	# bio-methanol (gasification)
	set_process_capex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_capex"))
	set_process_opex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_opex"))
	set_process_energy("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_energy"))
	set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", <-Variable("carbon_dioxide_per_methanol")>)

	# bio-methanol (SMR from biogas)
	set_process_capex("methanol_synthesis_bio_smr", Forecast("methanol_synthesis_bio_smr_capex"))
	set_process_opex("methanol_synthesis_bio_smr", Forecast("methanol_synthesis_bio_smr_opex"))
	set_process_energy("methanol_synthesis_bio_smr", Forecast("methanol_synthesis_bio_smr_energy"))
	set_process_wtt("methanol_synthesis_bio_smr", "carbon_dioxide", <-Variable("carbon_dioxide_per_methanol")>)

	# e-methanol
    set_process_capex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_capex"))
	set_process_opex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_opex"))
	set_process_energy("methanol_synthesis_electro_*", Forecast("methanol_synthesis_electro_energy"))
	set_process_wtt("methanol_synthesis_electro_*", "carbon_dioxide", <Variable("methanol_carbon_dioxide_conversion") - Variable("carbon_dioxide_per_methanol")>)

	# ethanol ----------------------------------------------------------------------------------------------------------

	# bio-ethanol
	set_process_capex("ethanol_synthesis_bio", Forecast("ethanol_synthesis_bio_capex"))
	set_process_opex("ethanol_synthesis_bio", Forecast("ethanol_synthesis_bio_opex"))
	set_process_energy("ethanol_synthesis_bio", Forecast("ethanol_synthesis_bio_energy"))
	set_process_wtt("ethanol_synthesis_bio", "carbon_dioxide", <-Variable("carbon_dioxide_per_ethanol")>)

	# diesel -----------------------------------------------------------------------------------------------------------

	# e-diesel
	set_process_capex("diesel_synthesis_electro_*", Timetable("diesel_synthesis_electro_capex"))
	set_process_opex("diesel_synthesis_electro_*", Timetable("diesel_synthesis_electro_opex"))
	set_process_energy("diesel_synthesis_electro_*", Forecast("diesel_synthesis_electro_energy"))
	set_process_wtt("diesel_synthesis_electro_*", "carbon_dioxide", <Variable("diesel_carbon_dioxide_conversion") - Variable("carbon_dioxide_per_diesel_electro")>)
}
