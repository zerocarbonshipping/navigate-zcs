# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# General nodes: ModelDefinition, BunkerOptions
#
# Attributes covered:
#   ModelDefinition: StartDate, EmissionsLifetime
#   BunkerOptions:   Solver, SolverMethod, SolutionTolerance, Threads,
#                    FairShareMaximumIterations, FairShareTolerance

ModelDefinition {
	StartDate = "01/01/2024"
	EmissionsLifetime = 20
}

BunkerOptions {
	Solver = AUTOMATIC
	SolverMethod = DETERMINISTIC
	SolutionTolerance = 1e-6
	Threads = 0
	FairShareMaximumIterations = 50
	FairShareTolerance = 0.1
}
