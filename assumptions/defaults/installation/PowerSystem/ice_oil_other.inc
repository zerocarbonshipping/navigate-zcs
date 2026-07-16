# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_oil_other" {
	Propulsion = Converter("propulsion_ice_oil_other")
	Electrical = Converter("electrical_ice_oil_other")
	Heat = Converter("heat_boiler_oil_other")

	CAPEX = Forecast("other_supply_system_oil_capex")
	OPEX = <Forecast("other_supply_system_oil_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
