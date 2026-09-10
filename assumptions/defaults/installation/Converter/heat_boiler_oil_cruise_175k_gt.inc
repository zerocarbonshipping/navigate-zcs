# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "heat_boiler_oil_cruise_175k_gt" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("cruise_175k_gt_heat_power_capacity")
	Efficiency = Variable("heat_oil_efficiency")

	Capex = Forecast("heat_oil_capex")
	Opex = Forecast("heat_oil_opex")
}
