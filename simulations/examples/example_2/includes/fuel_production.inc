# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------------- FUEL PRODUCTION --------------------------------------
#
# This file defines the fuels available in the Pacific regional bulk trade example.
# It includes both conventional fossil fuel oil and a bio-fuel alternative (FAME),
# along with their associated production plants, processes, and feedstocks.
#
# Regional supply and producer definitions are specified separately in producer.inc
# and regions.inc. FAME production is assumed to take place in Europe, with
# fossil fuels treated as globally available.
#
# ----------------------------------------------------------------------------------------

# FUEL OIL
# Conventional fossil marine fuel widely available in the region
Import Fuel "fossil_fuel_oil"

# FAME
# Renewable biodiesel (Fatty Acid Methyl Ester) produced from waste oils and fats
Import Fuel "fatty_acid_methyl_ester"

# FAME production plant located in Europe
Import Plant "plant_fatty_acid_methyl_ester"

Plant "plant_fatty_acid_methyl_ester" {
    Region = Region("europe")
    Source = Source("grid")
}

# FAME synthesis process using multiple feedstocks
Import Process "fatty_acid_methyl_ester_synthesis"
Import Feedstock "used_cooking_oil"
Import Feedstock "methanol_grey"
Import Feedstock "demineralized_water"

# Electricity Source
# FAME production is assumed to draw electricity from the regional grid
Import Source "grid"
