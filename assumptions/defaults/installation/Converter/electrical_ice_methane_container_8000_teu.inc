# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_methane_container_8000_teu" {
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("electrical_methane_minimum_pilot_fuel")

	PowerCapacity = Variable("container_8000_teu_electrical_power_capacity")
	Efficiency = Variable("electrical_methane_efficiency")

	CAPEX = Forecast("electrical_methane_capex")
	OPEX = Forecast("electrical_methane_opex")
	
	set_slip_fraction(METHANE, Variable("electrical_methane_methane_slip"))
}
