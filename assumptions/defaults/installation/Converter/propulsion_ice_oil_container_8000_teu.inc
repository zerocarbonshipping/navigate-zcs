# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_oil_container_8000_teu" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("container_8000_teu_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_container")
	Efficiency = Variable("propulsion_oil_efficiency")

	CAPEX = Forecast("propulsion_oil_capex")
	OPEX = Forecast("propulsion_oil_opex")
}
