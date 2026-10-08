# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

PowerSystem "ice_methane_lpg_carrier_84k_cbm" {
	Propulsion = Converter("propulsion_ice_methane_lpg_carrier_84k_cbm")
	Electrical = Converter("electrical_ice_methane_lpg_carrier_84k_cbm")
	Heat = Converter("heat_boiler_oil_lpg_carrier_84k_cbm")

	CAPEX = Forecast("lpg_carrier_84k_cbm_supply_system_methane_capex")
	OPEX = <Forecast("lpg_carrier_84k_cbm_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
