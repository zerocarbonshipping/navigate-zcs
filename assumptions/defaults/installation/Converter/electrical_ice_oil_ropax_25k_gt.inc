# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Converter "electrical_ice_oil_ropax_25k_gt" {
	MainFuelTypes = OIL

	PowerCapacity = Variable("ropax_25k_gt_electrical_power_capacity")
	Efficiency = Variable("electrical_oil_efficiency")

	CAPEX = Forecast("electrical_oil_capex")
	OPEX = Forecast("electrical_oil_opex")
}
