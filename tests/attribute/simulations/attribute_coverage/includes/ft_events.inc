# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EVENTS: timeline + SECTION_BOTH attribute updates grouped by theme
#
# Every SECTION_BOTH attribute is updated at least once in this file.
# Commands with SECTION_BOTH are also exercised here.

Start

# --- Initial FT commands (before first date) --------------------------------

Fleet "fleet_b" {
	set_allow_vessel("vessel_methanol", TRUE)
	set_allow_vessel("vessel_ammonia", FALSE)
}

# --- 2026: baseline ----------------------------------------------------------

Date "01-01-2026"

# --- 2027: Converter & Machinery updates ------------------------------------

Date "01-01-2027"

Converter "prop_oil" {
	Efficiency = 0.52
	MinimumPilotFuel = 0.0
	CAPEX = 1.1e6
	OPEX = 55000
	Lifetime = 25
	Replacement = 0.6
	set_slip_fraction(OIL, 0.0)
	set_consumption_ttw(OIL, "nitrous_oxide", 0.00020)
}

PowerSystem "ps_oil" {
	CAPEX = 10000
	OPEX = 1000
	Lifetime = 25
	Replacement = 0.9
}

Tank "tank_oil" {
	CAPEX = 110000
	OPEX = 5500
	Lifetime = 25
	Replacement = 0.6
}

Vessel "vessel_oil" {
	Lifetime = 25
	LeadTime = 1
	CAPEX = 52e6
	OPEX = 2.1e6
	CostOfCapital = 0.07
}

# --- 2028: Fleet management --------------------------------------------------

Date "01-01-2028"

Fleet "fleet_a" {
	TechnologyCostOfCapital = 0.07
	FixedScrapRate = 0.01
	AllowSecondaryScrapping = FALSE
	Inertia = 0.1
	Memory = 0.5
	InterFuelSensitivity = 0.6
	IntraFuelSensitivity = 0.02
	TechnologySensitivity = 1
	RetrofitFrequency = 4
	FuelConversionSensitivity = 3
	FuelConversionMinimumAge = 4
	AllowTechnologyApproximation = FALSE
	set_fuel_conversion_cost("vessel_oil", "vessel_methane", 12e6)
	set_newbuild_available("vessel_methane", TRUE)
	set_conversion_available("vessel_methane", TRUE)
}

Fleet "fleet_b" {
	set_allow_vessel("vessel_ammonia", TRUE)
	set_newbuild_available("vessel_ammonia", TRUE)
	set_conversion_available("vessel_ammonia", FALSE)
}

# --- 2029: Technology & Energy -----------------------------------------------

Date "01-01-2029"

Technology "tech_ees" {
	CAPEX = 110000
	OPEX = 5500
	Lifetime = 16
	Replacement = 0.35
	ShorePowerCapacity = 0.5
	set_energy_saving(PROPULSION, 0.06)
	set_energy_saving(ELECTRICAL, 0.04)
	set_energy_saving(HEAT, 0.03)
}

Technology "tech_shore" {
	set_external_power(ELECTRICAL, 6.0)
	set_power_transfer(PROPULSION, ELECTRICAL, Variable("var_shore_transfer"))
}

# --- 2030: Speed management --------------------------------------------------

Date "01-01-2030"

Fleet "fleet_a" {
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.4
	SpeedAlignment = AVERAGE
	AssumeReferenceSpeedOptimal = TRUE
	set_operational_saving_sea(PROPULSION, 0.06)
	set_operational_saving_port(ELECTRICAL, 0.04)
}

# --- 2031: Port & Bunkering -------------------------------------------------

Date "01-01-2031"

Port "port_a" {
	ShorePowerCost = 45
	ShorePowerConnectionShare = 0.15
	set_bunkering_allowed("blue_ammonia", TRUE)
	set_bunkering_limit("lng", 600000)
	set_bunkering_inertia("lng", 0.6)
	set_handling_cost("hfo", 22)
	set_bunker_price_overwrite("hfo", 620)
	set_bunker_wtt_overwrite("hfo", "carbon_dioxide", 0.60)
	set_shore_power_emission_factor("carbon_dioxide", 0.150)
}

Port "port_b" {
	ShorePowerCost = 55
	ShorePowerConnectionShare = 0.25
}

# --- 2032: Policy changes ----------------------------------------------------

Date "01-01-2032"

Regulation "reg_absolute" {
	Active = TRUE
	IncludeSlip = FALSE
	IntraFraction = 0.8
	InterFraction = 0.4
	ExtraFraction = 0.1
	RemedialCost = 150
	SharedThreshold = 900000
	AllowThresholdAdjustment = FALSE
	set_vessel_threshold("vessel_oil", 4500)
	set_vessel_threshold("vessel_methane", 4500)
	set_global_warming_potential("methane", 28)
	set_fuel_wtt("hfo", "carbon_dioxide", 0.65)
	set_fuel_ttw("hfo", "carbon_dioxide", 3.2)
	set_include_vessel("vessel_oil", TRUE)
}

Regulation "reg_intensity" {
	SharedThreshold = 45
	RemedialCost = 80
	set_vessel_threshold("vessel_methanol", 55)
}

Regulation "reg_transport" {
	set_vessel_threshold("vessel_methanol", 9)
	set_vessel_capacity("vessel_methanol", 8000)
}

Levy "levy_penalty" {
	Active = TRUE
	Level = 60
	LowerThreshold = 5
	UpperThreshold = 90
	IncludeSlip = FALSE
	set_global_warming_potential("methane", 28)
	set_fuel_wtt("lng", "carbon_dioxide", 0.55)
	set_fuel_ttw("lng", "carbon_dioxide", 2.80)
	set_include_vessel("vessel_methane", TRUE)
}

Levy "levy_both" {
	Level = 35
}

# --- 2033: Supply chain changes ----------------------------------------------

Date "01-01-2033"

Plant "plant_methanol" {
	CostOfCapital = 0.07
	Capacity = 1200
	Uptime = 0.92
	Lifetime = 25
	LeadTime = 3
	set_feed_transport("water", Transport("truck"))
	set_feed_distance("water", 120)
}

Process "methanol_synthesis" {
	Conversions = [4.0, 2.5]
}

Producer "producer_global" {
	Inertia = 0.15
	MinimumOfftakeDuration = 2
	FuelDemandSensitivity = 1.3
	FuelCostSensitivity = 0.6
	MaximumDevelopment = 6
	MaximumRampUp = 0.6
	JumpStartFraction = 0.15
	set_allow_plant("plant_methanol", TRUE)
	set_feed_constraint("water", 1.2e6)
	set_export_distribution("port_a", 1.0)
}

Region "region_a" {
	set_process_capex("methanol_synthesis", 170)
	set_process_opex("methanol_synthesis", 95)
	set_process_energy("methanol_synthesis", 0.50)
	set_process_lifetime("methanol_synthesis", 26)
	set_process_replacement("methanol_synthesis", 0.6)
	set_process_wtt("methanol_synthesis", "carbon_dioxide", -1.40)
	set_source_capex("source_renewable", 480)
	set_source_opex("source_renewable", 48)
	set_source_wtt("source_renewable", "carbon_dioxide", 0)
	set_feedstock_cost("water", 1.1)
	set_feedstock_wtt("water", "carbon_dioxide", 0)
	set_transport_cost("truck", 11)
	set_transport_wtt("truck", "carbon_dioxide", 0.09)
}

# --- 2034: Route, Variable, Calculator, Sensitivity changes ------------------

Date "01-01-2034"

Route "route_regional" {
	TimeAtSea = 0.70
	PortCalls = [105]
	ConditionDistribution = [1.0]
	Speeds = [11]
	CapacityUtilizations = [0.75]
}

Route "route_roundtrip" {
	PortDurations = [2.5, 2.5]
	Speeds = [11, 11]
	CapacityUtilizations = [0.85, 0.55]
	set_voyage_distribution("port_a", "port_b", 0.55)
	set_voyage_distribution("port_b", "port_a", 0.45)
}

Variable "var_efficiency" {
	Value = 0.55
	Addition = 0.01
	Multiplier = 1.1
	LowerBound = 0
	UpperBound = 1
}

Forecast "fc_trade_growth" {
	Addition = 0.005
	Multiplier = 1.05
	LowerBound = 0
	UpperBound = 1
}

Surface "surface_load" {
	Addition = 0.1
	Multiplier = 1.0
	LowerBound = 0
	UpperBound = INF
}

Timetable "timetable_cost" {
	Addition = 5
	Multiplier = 1.1
	LowerBound = 0
	UpperBound = INF
}

Fleet "fleet_a" {
	InterFuelSensitivity = 0.4
	FuelConversionSensitivity = 2.5
}

End
