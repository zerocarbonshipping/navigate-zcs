# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The ammonia powered bulk vessel incl. powersystem and converters

Vessel "bulk_ice_ammonia" {
	PowerSystem = PowerSystem("ice_ammonia") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("pilot_oil"), Tank("main_ammonia")]	
	PropulsionLoad = 10
}

PowerSystem "ice_ammonia" {
	Propulsion = Converter("propulsion_ice_ammonia")
	Electrical = Converter("electrical_ice_ammonia")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_ammonia" { 
	PowerCapacity = 50 			  
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05	
	Efficiency = 0.51
}

Converter "electrical_ice_ammonia" { 
	PowerCapacity = 10 
	MainFuelTypes = AMMONIA 
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
}
