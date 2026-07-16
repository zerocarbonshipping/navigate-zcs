# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_oil_tanker_7500_dwt" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("tanker_7500_dwt_propulsion_power_capacity")
	MinimumLoad = Variable("propulsion_minimum_load_tanker")
	Efficiency = Variable("propulsion_oil_efficiency")

	CAPEX = Forecast("propulsion_oil_capex")
	OPEX = Forecast("propulsion_oil_opex")
}
