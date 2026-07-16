# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_oil_container_15000_teu" {
	Propulsion = Converter("propulsion_ice_oil_container_15000_teu")
	Electrical = Converter("electrical_ice_oil_container_15000_teu")
	Heat = Converter("heat_boiler_oil_container_15000_teu")

	CAPEX = Forecast("container_15000_teu_supply_system_oil_capex")
	OPEX = <Forecast("container_15000_teu_supply_system_oil_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
