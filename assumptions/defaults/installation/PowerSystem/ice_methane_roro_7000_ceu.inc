# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_roro_7000_ceu" {
	Propulsion = Converter("propulsion_ice_methane_roro_7000_ceu")
	Electrical = Converter("electrical_ice_methane_roro_7000_ceu")
	Heat = Converter("heat_boiler_oil_roro_7000_ceu")

	CAPEX = Forecast("roro_7000_ceu_supply_system_methane_capex")
	OPEX = <Forecast("roro_7000_ceu_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
