# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from tanker_47k_dwt: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

PowerSystem "ice_methane_chemical_tanker_40k_dwt" {
	Propulsion = Converter("propulsion_ice_methane_chemical_tanker_40k_dwt")
	Electrical = Converter("electrical_ice_methane_chemical_tanker_40k_dwt")
	Heat = Converter("heat_boiler_oil_chemical_tanker_40k_dwt")

	CAPEX = Forecast("chemical_tanker_40k_dwt_supply_system_methane_capex")
	OPEX = <Forecast("chemical_tanker_40k_dwt_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
