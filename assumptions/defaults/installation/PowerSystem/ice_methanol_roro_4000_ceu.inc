# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methanol_roro_4000_ceu" {
	Propulsion = Converter("propulsion_ice_methanol_roro_4000_ceu")
	Electrical = Converter("electrical_ice_methanol_roro_4000_ceu")
	Heat = Converter("heat_boiler_oil_roro_4000_ceu")

	CAPEX = Forecast("roro_4000_ceu_supply_system_methanol_capex")
	OPEX = <Forecast("roro_4000_ceu_supply_system_methanol_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
