# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_oil_container_15000_teu" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("container_15000_teu_electrical_power_capacity")
	Efficiency = Variable("electrical_oil_efficiency")

	CAPEX = Forecast("electrical_oil_capex")
	OPEX = Forecast("electrical_oil_opex")
}
