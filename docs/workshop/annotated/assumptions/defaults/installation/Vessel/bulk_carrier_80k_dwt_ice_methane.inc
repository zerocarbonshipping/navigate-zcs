# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The dual-fuel LNG ship of this class.
Vessel "bulk_carrier_80k_dwt_ice_methane" {
	
	# A Surface, looked up by speed and cargo utilisation.
	PropulsionLoad = Surface("bulk_carrier_80k_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("bulk_carrier_80k_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("bulk_carrier_80k_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("bulk_carrier_80k_dwt_heat_load_sea")
	HeatLoadInPort = Variable("bulk_carrier_80k_dwt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methane_bulk_carrier_80k_dwt")
	# Two tanks: one for LNG, and one for the oil its engines need as pilot
	# fuel.
	Tanks = [Tank("main_methane_bulk_carrier_80k_dwt"), Tank("pilot_oil_bulk_carrier_80k_dwt")]
	
	Route = Route("operational_profile_bulk_carrier_80k_dwt")
	NominalCapacity = Variable("bulk_carrier_80k_dwt_nominal_capacity")
	Lifetime = Variable("bulk_carrier_80k_dwt_lifetime")
	
	# The hull's CAPEX is a Forecast, looked up by date. Most of the other
	# numbers are Variable nodes, a single number each.
	CAPEX = Forecast("bulk_carrier_80k_dwt_capex")
	OPEX = Forecast("bulk_carrier_80k_dwt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
