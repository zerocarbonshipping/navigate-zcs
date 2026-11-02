# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Port "*" {
	# Each port keeps bunkering at least 70 % of what it sold of each fuel the
	# year before.
	set_bunkering_inertia("*", 0.7)
}

# Fleet decision-process calibration.
#
# Each sensitivity is an odds ratio against a fixed reference change. For the cost-based choices
# (lower-is-better levelized cost of transport) a value below 1 penalizes a 10% higher cost; for the
# NPV-based choices (higher-is-better) a value above 1 rewards an NPV advantage equal to 5% of the
# summed ship CAPEX. A value of 1 means no preference.
Fleet "*" {
	# Each year, 60 % of the newbuilds follow the previous year's mix of ship
	# types.
	Inertia = 0.6
	InterFuelSensitivity = 0.75         # a 10% higher cost gives 25% lower odds of a fuel type
	IntraFuelSensitivity = 0.75         # a 10% higher cost gives 25% lower odds of a technology variant
	FuelConversionSensitivity = 2       # an NPV advantage of 5% of ship CAPEX doubles the odds
	TechnologySensitivity = 2           # an NPV advantage of 5% of ship CAPEX doubles the odds
}

# Producer decision-process calibration.
#
# FuelDemandSensitivity is higher-is-better (odds for a 10% higher expected demand); FuelCostSensitivity
# is lower-is-better (odds for a 10% higher levelized cost of fuel). A value of 1 means no preference.
Producer "*" {
	# Each year, 60 % of the plant build follows the previous year's mix of
	# plants.
	Inertia = 0.6
	FuelDemandSensitivity = 1.25        # a 10% higher expected demand gives 1.25x the odds of a pathway
	FuelCostSensitivity = 0.75          # a 10% higher LCoF gives 25% lower odds of a plant
}
