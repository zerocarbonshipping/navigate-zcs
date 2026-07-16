# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The methane powered container vessel incl. powersystem and converters

Vessel "container_ice_methane" {
	PowerSystem = PowerSystem("ice_methane") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("pilot_oil"), Tank("main_methane")]
	PropulsionLoad = 10
}

PowerSystem "ice_methane" {
	Propulsion = Converter("propulsion_ice_methane")
	Electrical = Converter("electrical_ice_methane")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_methane" { 
	PowerCapacity = 50 			  
	MainFuelTypes = METHANE 	
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.51
	set_slip_fraction(METHANE, 0.01)
}

Converter "electrical_ice_methane" { 
	PowerCapacity = 10 
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
	set_slip_fraction(METHANE, 0.01)
}
