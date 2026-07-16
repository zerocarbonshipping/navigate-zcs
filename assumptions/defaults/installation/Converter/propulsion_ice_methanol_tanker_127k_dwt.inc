# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_methanol_tanker_127k_dwt" {
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("propulsion_methanol_minimum_pilot_fuel")

	PowerCapacity = Variable("tanker_127k_dwt_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_tanker")
	Efficiency = Variable("propulsion_methanol_efficiency")

	CAPEX = Forecast("propulsion_methanol_capex")
	OPEX = Forecast("propulsion_methanol_opex")
}
