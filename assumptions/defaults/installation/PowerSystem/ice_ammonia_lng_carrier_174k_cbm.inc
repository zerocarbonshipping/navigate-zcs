# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

PowerSystem "ice_ammonia_lng_carrier_174k_cbm" {
	Propulsion = Converter("propulsion_ice_ammonia_lng_carrier_174k_cbm")
	Electrical = Converter("electrical_ice_ammonia_lng_carrier_174k_cbm")
	Heat = Converter("heat_boiler_oil_lng_carrier_174k_cbm")

	CAPEX = Forecast("lng_carrier_174k_cbm_supply_system_ammonia_capex")
	OPEX = <Forecast("lng_carrier_174k_cbm_supply_system_ammonia_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
