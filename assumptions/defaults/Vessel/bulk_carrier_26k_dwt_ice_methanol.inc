# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "bulk_carrier_26k_dwt_ice_methanol" {
	
	PropulsionLoad = Surface("bulk_carrier_26k_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("bulk_carrier_26k_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("bulk_carrier_26k_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("bulk_carrier_26k_dwt_heat_load_sea")
	HeatLoadInPort = Variable("bulk_carrier_26k_dwt_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methanol_bulk_carrier_26k_dwt")
	ElectricalConverter = Converter("electrical_ice_methanol_bulk_carrier_26k_dwt")
	HeatConverter = Converter("heat_boiler_oil_bulk_carrier_26k_dwt")
	Tanks = [Tank("main_methanol_bulk_carrier_26k_dwt"), Tank("pilot_oil_bulk_carrier_26k_dwt")]
	
	Route = Route("operational_profile_bulk_carrier_26k_dwt")
	NominalCapacity = Variable("bulk_carrier_26k_dwt_nominal_capacity")
	Lifetime = Variable("bulk_carrier_26k_dwt_lifetime")
	
	Capex = <Forecast("bulk_carrier_26k_dwt_capex") + Forecast("bulk_carrier_26k_dwt_supply_system_methanol_capex")>
	Opex = <Forecast("bulk_carrier_26k_dwt_opex") + Forecast("bulk_carrier_26k_dwt_supply_system_methanol_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
