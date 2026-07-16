# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of fuel processing

# Definition of "fuel_oil_process"
Process "fuel_oil_process" {				
	Feeds = [Feedstock("crude_oil")]
	Conversions = [1.0]						
}

# Definition of "methane_liquefaction_electro"
Process "methane_liquefaction_electro" {  
	Feeds = [Process("methane_synthesis_electro")]
	Conversions = [1]
}

# Definition of "methane_synthesis_electro" 
Process "methane_synthesis_electro" {  
	Feeds = [Feedstock("demineralized_water"), Feedstock("carbon_dioxide_biogenic")]
	Conversions = [0.5, 2.75]  
}


# Definition of "methanol_synthesis_bio_gasification"
Process "methanol_synthesis_bio_gasification" {
	Feeds = [Feedstock("organic_wet_waste"), Feedstock("dry_wood_biomass")]
	Conversions = [1.21, 1.21]
}

# Definition of "haber_bosch_ccs_integrated_blue"
Process "haber_bosch_ccs_integrated_blue" {				
	Feeds = [Process("nitrogen_air_seperation"), Feedstock("natural_gas")]
	Conversions = [0.64, 0.822]						
}

# Definition of "nitrogen_air_seperation"
Process "nitrogen_air_seperation" {
}
