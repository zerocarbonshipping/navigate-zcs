# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_ammonia_general_cargo" {
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("electrical_ammonia_minimum_pilot_fuel")

	PowerCapacity = Variable("general_cargo_electrical_power_capacity")
	Efficiency = Variable("electrical_ammonia_efficiency")

	CAPEX = Forecast("electrical_ammonia_capex")
	OPEX = Forecast("electrical_ammonia_opex")
	
	set_consumption_ttw(AMMONIA, "nitrous_oxide", Variable("electrical_ammonia_nitrous_oxide_release"))
}
