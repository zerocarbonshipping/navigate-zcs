# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "propulsion_ice_oil_cruise_100k_gt" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("cruise_100k_gt_propulsion_power_capacity")
	Efficiency = Variable("propulsion_oil_efficiency")

	Capex = Forecast("propulsion_oil_capex")
	Opex = Forecast("propulsion_oil_opex")
}
