# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_tug" {
	Propulsion = Converter("propulsion_ice_methane_tug")
	Electrical = Converter("electrical_ice_methane_tug")
	Heat = Converter("heat_boiler_oil_tug")

	CAPEX = Forecast("tug_supply_system_methane_capex")
	OPEX = <Forecast("tug_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
