# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------------- FUEL PRODUCTION --------------------------------------
#
# This file includes all components related to the production of fuels used in the example.
# It covers both conventional marine fuels and a renewable alternative, along with their
# associated production processes and feedstocks.
#
# The producer and regional differences are defined in the .inc files producer.inc and regions.inc
#
# ----------------------------------------------------------------------------------------

# LSFO
# Standard fossil fuel used in global shipping
Import Fuel "fossil_fuel_oil"

# Bio-Methanol
# Low-emission methanol produced from sustainable biomass. Enables compliance with EU regulations
# and allows fuel-switching behavior in both feeder and mainline vessels.
Import Fuel "methanol_bio"

# Methanol production facilities located in Europe
Import Plant "plant_methanol_bio_gasification"

Plant "plant_methanol_bio_gasification" {
    Region = Region("europe")
    Source = Source("grid")

    Capacity = Forecast("methanol_bio_gasification_plant_capacity")
}

# Methanol synthesis process feedstock
Import Process "methanol_synthesis_bio_gasification"
Import Feedstock "feedstock_biomethanol_gasification"

# Electricity Source
# Fuel production in both regions draws electricity from the connected power grid.
Import Source "grid"

# Overwritten from the default values due to our smaller scenario
Forecast "methanol_bio_gasification_plant_capacity" {
	Table = [
		"01-01-2030"	100
		"01-01-2050"	100
	]
	
	Extrapolate = LINEAR
}