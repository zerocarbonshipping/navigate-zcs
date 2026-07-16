# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "pilot_oil_ferry" {
	FuelTypes = OIL
	Size = Variable("tank_size_ferry")

	CAPEX = Forecast("tank_oil_capex")
	OPEX = <Forecast("tank_oil_capex") * Variable("tank_opex_percentage_of_capex")>
}
