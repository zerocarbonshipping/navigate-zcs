# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of region

Region "region" {
#set CapEx, OpEx, Process and feedstock WTT emissions for the different processes that produces the alternative fuels. The expensens and emissions related to the production of the fuels depend on the region.

### E-methane ###
	set_process_capex("methane_synthesis_electro", 100)
	set_process_opex("methane_liquefaction_electro", 88)
	set_process_energy("methane_synthesis_electro", 0.4)
	# liquefied e-methane
	set_process_capex("methane_liquefaction_electro", 200)
	set_process_energy("methane_liquefaction_electro", 0.6)
	# Set WTT feedstock emissions below:
	set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", -1)
	# Set WTT process emissions below:
	set_process_wtt("methane_liquefaction_electro", "carbon_dioxide", 0.5)

### Bio-methanol ###
	set_process_capex("methanol_synthesis_bio_gasification", 180)
	set_process_opex("methanol_synthesis_bio_gasification", 100)
	set_process_energy("methanol_synthesis_bio_gasification", 0.52)
	set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", -1.35)
	set_process_wtt("methanol_synthesis_bio_gasification", "methane", 0.00005)
	set_process_wtt("methanol_synthesis_bio_gasification", "nitrous_oxide", 0.00018)
	

### Blue ammonia ###
	set_process_capex("haber_bosch_ccs_integrated_blue", 200)
	set_process_opex("haber_bosch_ccs_integrated_blue", 50	) # combining ammonia plant opex and cost of CCS
	set_process_energy("haber_bosch_ccs_integrated_blue", 0.25)
	
	# Set WTT feedstock emissions below:
	set_feedstock_wtt("natural_gas", "carbon_dioxide", 0.11)
	set_feedstock_wtt("natural_gas", "methane", 0.0073)
	set_process_wtt("haber_bosch_ccs_integrated_blue", "carbon_dioxide", 0.180) #adding missing ccs of some carbon here
}

