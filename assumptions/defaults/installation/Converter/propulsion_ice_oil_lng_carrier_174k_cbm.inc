# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Converter "propulsion_ice_oil_lng_carrier_174k_cbm" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("lng_carrier_174k_cbm_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_gas_carrier")
	Efficiency = Variable("propulsion_oil_efficiency")

	CAPEX = Forecast("propulsion_oil_capex")
	OPEX = Forecast("propulsion_oil_opex")
}
