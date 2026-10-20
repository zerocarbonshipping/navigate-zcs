# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Converter "electrical_ice_oil_bulk_carrier_52k_dwt" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("bulk_carrier_52k_dwt_electrical_power_capacity")
	Efficiency = Variable("electrical_oil_efficiency")

	Capex = Forecast("electrical_oil_capex")
	Opex = Forecast("electrical_oil_opex")
}
