# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_methane_tanker_7500_dwt" {
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("propulsion_methane_minimum_pilot_fuel")

	PowerCapacity = Variable("tanker_7500_dwt_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_tanker")
	Efficiency = Variable("propulsion_methane_efficiency")

	CAPEX = Forecast("propulsion_methane_capex")
	OPEX = Forecast("propulsion_methane_opex")
	
	set_slip_fraction(METHANE, Variable("propulsion_methane_methane_slip"))
}
