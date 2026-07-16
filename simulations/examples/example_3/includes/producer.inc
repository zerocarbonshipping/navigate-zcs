# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ PRODUCER ----------------------------------------------
#
# This block defines the e-ammonia producer entity responsible for fuel supply. It is located
# in Europe. It links to a dedicated plant and is subject to regional capacity and development. 
#
# -------------------------------------------------------------------------------------

Producer "epc_europe" {
	Plants = [Plant("plant_ammonia_electro_alkaline")]

    # define existing production capacity
    InitialCapacity = [108]

    # define the number of plants that can be built per year
	MaximumDevelopment = 1
}
