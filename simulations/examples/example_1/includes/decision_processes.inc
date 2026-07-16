# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# --------------------------- DECISION PROCESSES ----------------------------------
#
# This file defines how quickly the fleet and producers can adopt new fuels or technologies
# over time. These settings act as behavioral levers, influencing the model’s flexibility 
# in switching between fuels or retrofitting ships.
#
# -----------------------------------------------------------------------------------

Fleet "*" {
	# Decision sensitivities for newbuilds (odds ratios; LCOT is lower-is-better, so use a value below 1)
	InterFuelSensitivity = 0.5 # Between fuel types: a 10% higher LCOT halves the odds
	IntraFuelSensitivity = 0.5 # Within a single fuel type

	# Sensitivity for fuel conversions (NPV vs ship CAPEX; higher-is-better, so use a value above 1)
	FuelConversionSensitivity = 2
}

Producer "producer_methanol_bio" {
	# Decision sensitivities for split between plants
    FuelDemandSensitivity = 1.25 # Between fuel pathways: a 10% higher expected demand gives 1.25x the odds
    FuelCostSensitivity = 0.5    # Within a pathway: a 10% higher LCoF halves the odds
}
