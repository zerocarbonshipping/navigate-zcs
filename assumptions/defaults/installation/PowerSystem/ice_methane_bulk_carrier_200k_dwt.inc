# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_bulk_carrier_200k_dwt" {
	Propulsion = Converter("propulsion_ice_methane_bulk_carrier_200k_dwt")
	Electrical = Converter("electrical_ice_methane_bulk_carrier_200k_dwt")
	Heat = Converter("heat_boiler_oil_bulk_carrier_200k_dwt")

	CAPEX = Forecast("bulk_carrier_200k_dwt_supply_system_methane_capex")
	OPEX = <Forecast("bulk_carrier_200k_dwt_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
