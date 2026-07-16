# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_methane_cruise_175k_gt" {
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("propulsion_methane_minimum_pilot_fuel")

	PowerCapacity = Variable("cruise_175k_gt_propulsion_power_capacity")
	Efficiency = Variable("propulsion_methane_efficiency")

	CAPEX = Forecast("propulsion_methane_capex")
	OPEX = Forecast("propulsion_methane_opex")
	
	set_slip_fraction(METHANE, Variable("propulsion_methane_methane_slip"))
}
