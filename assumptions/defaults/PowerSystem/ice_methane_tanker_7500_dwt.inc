# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_tanker_7500_dwt" {
	Propulsion = Converter("propulsion_ice_methane_tanker_7500_dwt")
	Electrical = Converter("electrical_ice_methane_tanker_7500_dwt")
	Heat = Converter("heat_boiler_oil_tanker_7500_dwt")

	Capex = Forecast("tanker_7500_dwt_supply_system_methane_capex")
	Opex = <Forecast("tanker_7500_dwt_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
