# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Converter "electrical_ice_ammonia_lpg_carrier_84k_cbm" {
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("electrical_ammonia_minimum_pilot_fuel")

	PowerCapacity = Variable("lpg_carrier_84k_cbm_electrical_power_capacity")
	Efficiency = Variable("electrical_ammonia_efficiency")

	CAPEX = Forecast("electrical_ammonia_capex")
	OPEX = Forecast("electrical_ammonia_opex")
	
	set_consumption_ttw(AMMONIA, "nitrous_oxide", Variable("electrical_ammonia_nitrous_oxide_release"))
}
