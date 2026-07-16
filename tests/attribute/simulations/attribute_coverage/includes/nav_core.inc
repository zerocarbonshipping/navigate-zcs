# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# General nodes: ModelDefinition, BunkerLogistics, BunkerOptions
#
# Attributes covered:
#   ModelDefinition: StartDate, EmissionsLifetime, EnableOffsetting, OffsettingCost
#   BunkerLogistics: LiquidMarketFuels
#   BunkerOptions:   Solver, SolverMethod, SolutionTolerance, Threads,
#                    FairShareMaximumIterations, FairShareTolerance
#
# Commands covered:
#   BunkerLogistics: set_distance, set_transport_cost, set_transport_wtt

ModelDefinition {
	StartDate = "01/01/2024"
	EmissionsLifetime = 20
	EnableOffsetting = TRUE
	OffsettingCost = 200
}

BunkerLogistics {
	LiquidMarketFuels = [Fuel("hfo"), Fuel("lng"), Fuel("blue_ammonia")]
	set_distance("*", "*", 1000)
	set_transport_cost("*", 0.1)
	set_transport_wtt("*", "carbon_dioxide", 0.01)
}

BunkerOptions {
	Solver = AUTOMATIC
	SolverMethod = DETERMINISTIC
	SolutionTolerance = 1e-6
	Threads = 0
	FairShareMaximumIterations = 50
	FairShareTolerance = 0.1
}
