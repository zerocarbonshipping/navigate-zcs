# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_oil_container_4500_teu" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("container_4500_teu_electrical_power_capacity")
	Efficiency = Variable("electrical_oil_efficiency")

	Capex = Forecast("electrical_oil_capex")
	Opex = Forecast("electrical_oil_opex")
}
