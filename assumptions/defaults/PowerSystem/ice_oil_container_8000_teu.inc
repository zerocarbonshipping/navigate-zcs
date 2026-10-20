# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_oil_container_8000_teu" {
	Propulsion = Converter("propulsion_ice_oil_container_8000_teu")
	Electrical = Converter("electrical_ice_oil_container_8000_teu")
	Heat = Converter("heat_boiler_oil_container_8000_teu")

	Capex = Forecast("container_8000_teu_supply_system_oil_capex")
	Opex = <Forecast("container_8000_teu_supply_system_oil_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
