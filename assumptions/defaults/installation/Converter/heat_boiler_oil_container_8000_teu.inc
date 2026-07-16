# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "heat_boiler_oil_container_8000_teu" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("container_8000_teu_heat_power_capacity")
	Efficiency = Variable("heat_oil_efficiency")

	CAPEX = Forecast("heat_oil_capex")
	OPEX = Forecast("heat_oil_opex")
}
