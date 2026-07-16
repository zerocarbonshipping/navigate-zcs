# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_ammonia_offshore" {
	Propulsion = Converter("propulsion_ice_ammonia_offshore")
	Electrical = Converter("electrical_ice_ammonia_offshore")
	Heat = Converter("heat_boiler_oil_offshore")

	CAPEX = Forecast("offshore_supply_system_ammonia_capex")
	OPEX = <Forecast("offshore_supply_system_ammonia_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
