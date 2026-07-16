# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The fuel oil powered container vessel incl. powersystem and converters

Vessel "container_ice_oil" {
	PowerSystem = PowerSystem("ice_oil") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("main_oil")]						
	PropulsionLoad = 10
}

PowerSystem "ice_oil" {
	Propulsion = Converter("propulsion_ice_oil")
	Electrical = Converter("electrical_ice_oil")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_oil" { 
	PowerCapacity = 50 			  
	MainFuelTypes = OIL
	Efficiency = 0.51
}

Converter "electrical_ice_oil" { 
	PowerCapacity = 10 
	MainFuelTypes = OIL
	Efficiency = 0.5
}
 
Converter "heat_boiler_oil" {
	PowerCapacity = 5  
	MainFuelTypes = OIL
	Efficiency = 0.5
}
