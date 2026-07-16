# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_methanol_container_4500_teu" {
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("electrical_methanol_minimum_pilot_fuel")

	PowerCapacity = Variable("container_4500_teu_electrical_power_capacity")
	Efficiency = Variable("electrical_methanol_efficiency")

	CAPEX = Forecast("electrical_methanol_capex")
	OPEX = Forecast("electrical_methanol_opex")
}
