# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------- FUEL PRODUCTION ---------------------------------
#
# This file defines the fuels and production pathways available in the Baltic 
# tanker example. Conventional fuel oil is included as the fossil baseline, widely
# available at all major ports in the region. Alongside this, the example
# introduces electro-ammonia as a renewable alternative fuel.
#
# Electro-ammonia is assumed to be produced in Europe, using renewable
# electricity from the grid to power hydrogen electrolysis and nitrogen 
# separation. The hydrogen and nitrogen are then combined via a Haber-Bosch 
# process to synthesize ammonia. This reflects a likely future production 
# pathway for low-carbon fuels in Northern Europe, supported by the expansion 
# of wind and other renewable energy resources.
#
# By comparing fossil fuel with electro-ammonia, the example highlights both
# the technical feasibility and the cost/emissions trade-offs of adopting an 
# electro-fuel in short-sea tanker operations in the Baltic.
#
# ---------------------------------------------------------------------------------

Import Fuel "fossil_fuel_oil"

# Electro-ammonia – renewable ammonia produced from hydrogen and nitrogen
Import Fuel "ammonia_electro"

# Production plant for electro-ammonia located in Europe
Import Plant "plant_ammonia_electro_alkaline"

Plant "plant_ammonia_electro_alkaline" {
    Region = Region("europe")
    Source = Source("renewable")  # stand-alone renewable electricity production
}

# Production processes for electro-ammonia (Haber-Bosch + supporting steps)
Import Process "electrolysis_stack_alkaline"
Import Process "ammonia_synthesis_electro_alkaline"
Import Process "hydrogen_electro_alkaline"
Import Process "nitrogen_air_separation"
Import Feedstock "demineralized_water"

# Electricity source definition
Import Source "renewable"
