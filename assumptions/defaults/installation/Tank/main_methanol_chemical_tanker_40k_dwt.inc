# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from tanker_47k_dwt: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_methanol_chemical_tanker_40k_dwt" {
	FuelTypes = METHANOL
	Size = Variable("tank_size_chemical_tanker_40k_dwt")

	CAPEX = Forecast("tank_methanol_capex")
	OPEX = <Forecast("tank_methanol_capex") * Variable("tank_opex_percentage_of_capex")>
}
