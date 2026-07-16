# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The methanol powered bulk vessel incl. powersystem and converters

Vessel "bulk_ice_methanol" {
	PowerSystem = PowerSystem("ice_methanol") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("pilot_oil"), Tank("main_methanol")] 
	PropulsionLoad = 10
}

PowerSystem "ice_methanol" {
	Propulsion = Converter("propulsion_ice_methanol")
	Electrical = Converter("electrical_ice_methanol")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_methanol" { 
	PowerCapacity = 50 			  
	MainFuelTypes = METHANOL 
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05	
	Efficiency = 0.51
}

Converter "electrical_ice_methanol" { 
	PowerCapacity = 10 
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
}
