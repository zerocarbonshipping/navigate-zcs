# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Model definition and solver pin shared by every combination deck. HiGHS is
# pinned so a run does not depend on a Gurobi licence being present.
ModelDefinition {
	StartDate = "01-01-2026"
	EmissionsLifetime = 100
}

BunkerOptions {
	Solver = HIGHS
}

# The global warming potentials are pinned as constants, since every emission
# intensity a test reads derives from them.
Import Emission "carbon_dioxide"
Import Emission "methane"

Emission "carbon_dioxide" {
	GlobalWarmingPotential = 1
}

Emission "methane" {
	GlobalWarmingPotential = 30         # ton CO2-eq/ton
}
