# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from tanker_47k_dwt: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Vessel "chemical_tanker_40k_dwt_ice_methanol" {
	
	PropulsionLoad = Surface("chemical_tanker_40k_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("chemical_tanker_40k_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("chemical_tanker_40k_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("chemical_tanker_40k_dwt_heat_load_sea")
	HeatLoadInPort = Variable("chemical_tanker_40k_dwt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methanol_chemical_tanker_40k_dwt")
	Tanks = [Tank("main_methanol_chemical_tanker_40k_dwt"), Tank("pilot_oil_chemical_tanker_40k_dwt")]
	
	Route = Route("operational_profile_chemical_tanker_40k_dwt")
	NominalCapacity = Variable("chemical_tanker_40k_dwt_nominal_capacity")
	Lifetime = Variable("chemical_tanker_40k_dwt_lifetime")
	
	CAPEX = Forecast("chemical_tanker_40k_dwt_capex")
	OPEX = Forecast("chemical_tanker_40k_dwt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
