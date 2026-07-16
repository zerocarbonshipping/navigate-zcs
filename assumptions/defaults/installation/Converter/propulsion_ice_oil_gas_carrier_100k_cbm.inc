# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_oil_gas_carrier_100k_cbm" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("gas_carrier_100k_cbm_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_gas_carrier")
	Efficiency = Variable("propulsion_oil_efficiency")

	CAPEX = Forecast("propulsion_oil_capex")
	OPEX = Forecast("propulsion_oil_opex")
}
