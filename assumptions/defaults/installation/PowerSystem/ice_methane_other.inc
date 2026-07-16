# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_other" {
	Propulsion = Converter("propulsion_ice_methane_other")
	Electrical = Converter("electrical_ice_methane_other")
	Heat = Converter("heat_boiler_oil_other")

	CAPEX = Forecast("other_supply_system_methane_capex")
	OPEX = <Forecast("other_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
