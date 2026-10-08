# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from tanker_47k_dwt: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_ammonia_chemical_tanker_40k_dwt" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_chemical_tanker_40k_dwt")

	CAPEX = Forecast("tank_ammonia_capex_chemical_tanker_40k_dwt")
	OPEX = <Forecast("tank_ammonia_capex_chemical_tanker_40k_dwt") * Variable("tank_opex_percentage_of_capex")>
}
