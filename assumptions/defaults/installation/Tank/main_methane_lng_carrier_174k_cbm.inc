# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_methane_lng_carrier_174k_cbm" {
	FuelTypes = METHANE
	Size = Variable("tank_size_lng_carrier_174k_cbm")

	CAPEX = Forecast("tank_methane_capex_lng_carrier_174k_cbm")
	OPEX = <Forecast("tank_methane_capex_lng_carrier_174k_cbm") * Variable("tank_opex_percentage_of_capex")>
}
