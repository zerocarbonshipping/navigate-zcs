# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_oil_roro_4000_ceu" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("roro_4000_ceu_electrical_power_capacity")
	Efficiency = Variable("electrical_oil_efficiency")

	Capex = Forecast("electrical_oil_capex")
	Opex = Forecast("electrical_oil_opex")
}
