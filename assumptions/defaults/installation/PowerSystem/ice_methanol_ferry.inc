# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methanol_ferry" {
	Propulsion = Converter("propulsion_ice_methanol_ferry")
	Electrical = Converter("electrical_ice_methanol_ferry")
	Heat = Converter("heat_boiler_oil_ferry")

	CAPEX = Forecast("ferry_supply_system_methanol_capex")
	OPEX = <Forecast("ferry_supply_system_methanol_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
