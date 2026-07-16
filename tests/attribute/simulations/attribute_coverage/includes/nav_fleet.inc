# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Fleet nodes: Converter, PowerSystem, Tank, Technology, Vessel, Fleet
#
# Attributes covered:
#   Converter:   PowerCapacity, MinimumLoad, MainFuelTypes, PilotFuelTypes,
#                MinimumPilotFuel, Efficiency, CAPEX, OPEX, Lifetime, Replacement
#   PowerSystem: Propulsion, Electrical, Heat, CAPEX, OPEX, Lifetime, Replacement
#   Tank:        FuelTypes, Size, CAPEX, OPEX, Lifetime, Replacement
#   Technology:  CAPEX, OPEX, Lifetime, Replacement, ShorePowerCapacity
#   Vessel:      PropulsionLoad, ElectricalLoadAtSea, ElectricalLoadInPort,
#                HeatLoadAtSea, HeatLoadInPort, FuelType, PowerSystem, Tanks,
#                Route, NominalCapacity, Lifetime, LeadTime,
#                CAPEX, OPEX, CostOfCapital
#   Fleet:       Vessels, InitialVessels, TradeGrowth, InitialSplit,
#                InitialAgeDistribution, Orderbooks, Technologies,
#                TechnologyCostOfCapital, FixedScrapRate, AllowSecondaryScrapping,
#                Inertia, Memory, InterFuelSensitivity, IntraFuelSensitivity,
#                AllowSpeedManagement, MaximumSpeedChange, SpeedAlignment,
#                AssumeReferenceSpeedOptimal, TechnologySensitivity, RetrofitFrequency,
#                FuelConversionSensitivity, FuelConversionMinimumAge,
#                AllowTechnologyApproximation
#
# Commands covered:
#   Converter:  set_slip_fraction, set_consumption_ttw
#   Technology: set_energy_saving, set_external_power, set_power_transfer
#   Fleet:      set_fuel_conversion_cost, set_allow_vessel, set_newbuild_available,
#               set_conversion_available, set_newbuild_limit,
#               set_newbuild_technology_limit, set_retrofit_technology_limit,
#               set_fuel_conversion_limit, set_operational_saving_sea,
#               set_operational_saving_port, set_initial_technology_share

# --- Converters --------------------------------------------------------------

Converter "prop_oil" {
	PowerCapacity = 50
	MinimumLoad = 0.1
	MainFuelTypes = OIL
	Efficiency = 0.51
	CAPEX = 1e6
	OPEX = 50000
	Lifetime = 25
	Replacement = 0.5
	set_consumption_ttw(OIL, "nitrous_oxide", 0.00018)
}

Converter "elec_oil" {
	PowerCapacity = 10
	MainFuelTypes = OIL
	Efficiency = 0.5
}

Converter "heat_oil" {
	PowerCapacity = 5
	MainFuelTypes = OIL
	Efficiency = 0.85
}

Converter "prop_methane" {
	PowerCapacity = 50
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.51
	set_slip_fraction(METHANE, 0.01)
}

Converter "elec_methane" {
	PowerCapacity = 10
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
	set_slip_fraction(METHANE, 0.01)
}

Converter "prop_methanol" {
	PowerCapacity = 50
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.51
}

Converter "elec_methanol" {
	PowerCapacity = 10
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
}

Converter "prop_ammonia" {
	PowerCapacity = 50
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.51
}

Converter "elec_ammonia" {
	PowerCapacity = 10
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
}

# --- Power Systems -----------------------------------------------------------

PowerSystem "ps_oil" {
	Propulsion = Converter("prop_oil")
	Electrical = Converter("elec_oil")
	Heat = Converter("heat_oil")
	CAPEX = 0
	OPEX = 0
	Lifetime = 25
	Replacement = 1.0
}

PowerSystem "ps_methane" {
	Propulsion = Converter("prop_methane")
	Electrical = Converter("elec_methane")
	Heat = Converter("heat_oil")
}

PowerSystem "ps_methanol" {
	Propulsion = Converter("prop_methanol")
	Electrical = Converter("elec_methanol")
	Heat = Converter("heat_oil")
}

PowerSystem "ps_ammonia" {
	Propulsion = Converter("prop_ammonia")
	Electrical = Converter("elec_ammonia")
	Heat = Converter("heat_oil")
}

# --- Tanks -------------------------------------------------------------------

Tank "tank_oil" {
	FuelTypes = OIL
	Size = 9000
	CAPEX = 100000
	OPEX = 5000
	Lifetime = 25
	Replacement = 0.5
}

Tank "tank_methane" {
	FuelTypes = METHANE
	Size = 9000
}

Tank "tank_methanol" {
	FuelTypes = METHANOL
	Size = 9000
}

Tank "tank_ammonia" {
	FuelTypes = AMMONIA
	Size = 9000
}

Tank "tank_pilot" {
	FuelTypes = OIL
	Size = 1000
}

# --- Technologies ------------------------------------------------------------

Technology "tech_ees" {
	CAPEX = 100000
	OPEX = 5000
	Lifetime = 15
	Replacement = 0.3
	ShorePowerCapacity = 0
	set_energy_saving(PROPULSION, 0.05)
	set_energy_saving(ELECTRICAL, 0.03)
	set_energy_saving(HEAT, 0.02)
}

Technology "tech_shore" {
	CAPEX = 200000
	OPEX = 10000
	Lifetime = 20
	Replacement = 0.5
	ShorePowerCapacity = 5.0
	set_external_power(ELECTRICAL, 5.0)
	set_power_transfer(PROPULSION, ELECTRICAL, Variable("var_shore_transfer"))
}

# --- Vessels -----------------------------------------------------------------

Vessel "vessel_oil" {
	PowerSystem = PowerSystem("ps_oil")
	Route = Route("route_regional")
	NominalCapacity = 8000
	Tanks = [Tank("tank_oil")]
	PropulsionLoad = 10
	ElectricalLoadAtSea = 2
	ElectricalLoadInPort = 1
	HeatLoadAtSea = 1
	HeatLoadInPort = 0.5
	Lifetime = 25
	LeadTime = 2
	CAPEX = 50e6
	OPEX = 2e6
	CostOfCapital = 0.08
}

Vessel "vessel_methane" {
	PowerSystem = PowerSystem("ps_methane")
	Route = Route("route_regional")
	NominalCapacity = 8000
	Tanks = [Tank("tank_methane"), Tank("tank_pilot")]
	PropulsionLoad = 10
	FuelType = METHANE
}

Vessel "vessel_methanol" {
	PowerSystem = PowerSystem("ps_methanol")
	Route = Route("route_regional")
	NominalCapacity = 8000
	Tanks = [Tank("tank_methanol"), Tank("tank_pilot")]
	PropulsionLoad = 10
}

Vessel "vessel_ammonia" {
	PowerSystem = PowerSystem("ps_ammonia")
	Route = Route("route_regional")
	NominalCapacity = 8000
	Tanks = [Tank("tank_ammonia"), Tank("tank_pilot")]
	PropulsionLoad = 10
}

# --- Fleets ------------------------------------------------------------------

Fleet "fleet_a" {
	Vessels = [Vessel("vessel_oil"), Vessel("vessel_methane")]
	InitialVessels = 100
	TradeGrowth = Forecast("fc_trade_growth")
	InitialSplit = [1.0, 0.0]
	InitialAgeDistribution = [Curve("curve_age_a"), Curve("curve_age_b")]
	Orderbooks = [Forecast("fc_orderbook_a"), Forecast("fc_orderbook_b")]
	Technologies = [Technology("tech_ees"), Technology("tech_shore")]
	TechnologyCostOfCapital = 0.08
	FixedScrapRate = 0
	AllowSecondaryScrapping = TRUE
	Inertia = 0.0
	Memory = 1
	InterFuelSensitivity = 0.5
	IntraFuelSensitivity = 0.01
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.3
	SpeedAlignment = INDIVIDUAL
	AssumeReferenceSpeedOptimal = FALSE
	TechnologySensitivity = 1
	RetrofitFrequency = 5
	FuelConversionSensitivity = 2
	FuelConversionMinimumAge = 5
	AllowTechnologyApproximation = TRUE
	set_fuel_conversion_cost("vessel_oil", "vessel_methane", 10e6)
	set_allow_vessel("vessel_oil", TRUE)
	set_allow_vessel("vessel_methane", TRUE)
	set_newbuild_available("vessel_oil", TRUE)
	set_newbuild_available("vessel_methane", TRUE)
	set_conversion_available("vessel_methane", TRUE)
	set_newbuild_limit("vessel_oil", 1.0)
	set_newbuild_technology_limit("tech_ees", 0.06)
	set_retrofit_technology_limit("tech_ees", 0.04)
	set_fuel_conversion_limit("vessel_oil", "vessel_methane", 1.0)
	set_operational_saving_sea(PROPULSION, Forecast("fc_operational_saving"))
	set_operational_saving_port(ELECTRICAL, 0.03)
	set_initial_technology_share("vessel_oil", "tech_ees", Curve("curve_tech_uptake"))
}

Fleet "fleet_b" {
	Vessels = [Vessel("vessel_methanol"), Vessel("vessel_ammonia")]
	InitialVessels = 100
	InitialSplit = [1.0, 0.0]
	TradeGrowth = 0.03
	InterFuelSensitivity = 1
	IntraFuelSensitivity = 0.5
}
