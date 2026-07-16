# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_oil_offshore" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("offshore_electrical_power_capacity")
	Efficiency = Variable("electrical_oil_efficiency")

	CAPEX = Forecast("electrical_oil_capex")
	OPEX = Forecast("electrical_oil_opex")
}
