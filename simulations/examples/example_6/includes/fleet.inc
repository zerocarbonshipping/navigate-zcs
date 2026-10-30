# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FLEET - large Rhine motor cargo vessels, built from the library's general cargo
# vessels and resized with the INVENTED values of placeholders.inc.
# The fuel-system and tank costs are a seagoing ship's.
# Each vessel gets its own propulsion and electrical Converters (the engine power
# sits there) and its own PowerSystem naming them. Heat converter, tanks, fuel
# options and machinery costs are the library's.

Copy Converter "propulsion_ice_oil_general_cargo"      "rhine_propulsion_oil"
Copy Converter "propulsion_ice_methane_general_cargo"  "rhine_propulsion_methane"
Copy Converter "propulsion_ice_methanol_general_cargo" "rhine_propulsion_methanol"
Copy Converter "electrical_ice_oil_general_cargo"      "rhine_electrical_oil"
Copy Converter "electrical_ice_methane_general_cargo"  "rhine_electrical_methane"
Copy Converter "electrical_ice_methanol_general_cargo" "rhine_electrical_methanol"

Converter "rhine_propulsion_*" {
	PowerCapacity = Variable("rhine_propulsion_power_capacity")   # INVENTED 1.5 MW
}
Converter "rhine_electrical_*" {
	PowerCapacity = Variable("rhine_electrical_power_capacity")   # INVENTED 0.2 MW
}

Copy PowerSystem "ice_oil_general_cargo"      "rhine_ice_oil"
Copy PowerSystem "ice_methane_general_cargo"  "rhine_ice_methane"
Copy PowerSystem "ice_methanol_general_cargo" "rhine_ice_methanol"

PowerSystem "rhine_ice_oil" {
	Propulsion = Converter("rhine_propulsion_oil")
	Electrical = Converter("rhine_electrical_oil")
}
PowerSystem "rhine_ice_methane" {
	Propulsion = Converter("rhine_propulsion_methane")
	Electrical = Converter("rhine_electrical_methane")
}
PowerSystem "rhine_ice_methanol" {
	Propulsion = Converter("rhine_propulsion_methanol")
	Electrical = Converter("rhine_electrical_methanol")
}

Copy Vessel "general_cargo_ice_oil"      "rhine_oil"
Copy Vessel "general_cargo_ice_methane"  "rhine_lng"
Copy Vessel "general_cargo_ice_methanol" "rhine_methanol"

Vessel "rhine_*" {
	PropulsionLoad = Curve("rhine_propulsion_load")                    # INVENTED
	ElectricalLoadAtSea = Variable("rhine_electrical_load_sea")        # INVENTED 0.1 MW
	ElectricalLoadInPort = Variable("rhine_electrical_load_port")      # INVENTED 0.05 MW
	NominalCapacity = Variable("rhine_nominal_capacity")               # INVENTED 3000 t
	Lifetime = Variable("rhine_lifetime")                              # INVENTED 40 years
	CAPEX = Forecast("rhine_hull_capex")                               # INVENTED 6 M USD, hull only
}

Vessel "rhine_oil"      { PowerSystem = PowerSystem("rhine_ice_oil") }
Vessel "rhine_lng"      { PowerSystem = PowerSystem("rhine_ice_methane") }
Vessel "rhine_methanol" { PowerSystem = PowerSystem("rhine_ice_methanol") }

Fleet "rhine_fleet" {
	Vessels = [Vessel("rhine_oil"), Vessel("rhine_lng"), Vessel("rhine_methanol")]

	InitialVessels = Variable("rhine_initial_vessels")   # INVENTED 300
	InitialSplit = [1.0, 0.0, 0.0]                       # all on fuel oil
	InitialAgeDistribution = [Curve("rhine_age_dist"), 0, 0]

	# Library trade growth of the general cargo class (not inland-specific).
	TradeGrowth = Forecast("trade_growth_general_cargo")

	# No set_fuel_conversion_cost: ships cannot be converted to another fuel.
	# Orderbooks omitted: the library's are sized for the world fleet.

	AllowSpeedManagement = FALSE   # the waterway sets the speed
}
