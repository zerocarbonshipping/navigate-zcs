# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Converter "heat_boiler_oil_lng_carrier_174k_cbm" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("lng_carrier_174k_cbm_heat_power_capacity")
	Efficiency = Variable("heat_oil_efficiency")

	CAPEX = Forecast("heat_oil_capex")
	OPEX = Forecast("heat_oil_opex")
}
