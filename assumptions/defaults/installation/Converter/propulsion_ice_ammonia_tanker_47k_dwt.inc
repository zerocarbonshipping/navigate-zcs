# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_ammonia_tanker_47k_dwt" {
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("propulsion_ammonia_minimum_pilot_fuel")

	PowerCapacity = Variable("tanker_47k_dwt_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_tanker")
	Efficiency = Variable("propulsion_ammonia_efficiency")

	CAPEX = Forecast("propulsion_ammonia_capex")
	OPEX = Forecast("propulsion_ammonia_opex")
	
	set_consumption_ttw(AMMONIA, "nitrous_oxide", Variable("propulsion_ammonia_nitrous_oxide_release"))
}
