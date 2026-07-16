# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_gas_carrier_100k_cbm" {
	Propulsion = Converter("propulsion_ice_methane_gas_carrier_100k_cbm")
	Electrical = Converter("electrical_ice_methane_gas_carrier_100k_cbm")
	Heat = Converter("heat_boiler_oil_gas_carrier_100k_cbm")

	CAPEX = Forecast("gas_carrier_100k_cbm_supply_system_methane_capex")
	OPEX = <Forecast("gas_carrier_100k_cbm_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
