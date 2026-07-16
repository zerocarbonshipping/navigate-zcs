# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of fuel production plants


# e-methane -------------------------------------------------------
Plant "plant_methane_electro" {     #e-methane plant difinition
	Fuel = Fuel("methane_electro")      #difinition of fuel: e-methane with CCS from point source
	Process = Process("methane_liquefaction_electro")  #Process turning methane gas into LBiquefied Methane - the condition methane needs to be turned into to be a sailable fuel
	Region = Region("region")        #Definition of the region where the plant is positioned
	Source = Source("renewable")  #sustainable e-fuels are sourced from wind and solar power
	Capacity = 1000   #The plant capacity
}


# bio-methanol -------------------------------------------------------
Plant "plant_methanol_bio_gasification" {
	Fuel = Fuel("methanol_bio")
	Process = Process("methanol_synthesis_bio_gasification")
	Region = Region("region")
	Source = Source("grid")
	
	Capacity = 1000
}

#  blue ammonia -------------------------------------------------------
Plant "plant_ammonia_blue" {
	Fuel = Fuel("ammonia_blue")
	Process = Process("haber_bosch_ccs_integrated_blue")
	Region = Region("region")
	Source = Source("grid")
	Capacity = 1000
}

