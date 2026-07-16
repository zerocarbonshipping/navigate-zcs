# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_ammonia_tanker_300k_dwt" {
	Propulsion = Converter("propulsion_ice_ammonia_tanker_300k_dwt")
	Electrical = Converter("electrical_ice_ammonia_tanker_300k_dwt")
	Heat = Converter("heat_boiler_oil_tanker_300k_dwt")

	CAPEX = Forecast("tanker_300k_dwt_supply_system_ammonia_capex")
	OPEX = <Forecast("tanker_300k_dwt_supply_system_ammonia_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
