# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_ammonia_container_4500_teu" {
	Propulsion = Converter("propulsion_ice_ammonia_container_4500_teu")
	Electrical = Converter("electrical_ice_ammonia_container_4500_teu")
	Heat = Converter("heat_boiler_oil_container_4500_teu")

	CAPEX = Forecast("container_4500_teu_supply_system_ammonia_capex")
	OPEX = <Forecast("container_4500_teu_supply_system_ammonia_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
