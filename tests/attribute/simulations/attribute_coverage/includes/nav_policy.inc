# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Policy nodes: Regulation, Levy
#
# Attributes covered:
#   Regulation: Active, Scheme, Jurisdiction, Emissions, Fuels, Scope,
#               EmissionsLifetime, IncludeSlip, Measure,
#               IntraFraction, InterFraction, ExtraFraction, RemedialCost,
#               AllowThresholdAdjustment
#   Levy:       Active, Scheme, Jurisdiction, Emissions, Fuels, Scope,
#               EmissionsLifetime, IncludeSlip, Level,
#               LowerThreshold, UpperThreshold
#
# Commands covered:
#   Regulation: set_include_vessel, set_global_warming_potential, set_fuel_wtt,
#               set_fuel_ttw, set_vessel_threshold, set_vessel_capacity
#   Levy:       set_include_vessel, set_global_warming_potential, set_fuel_wtt,
#               set_fuel_ttw

# ABSOLUTE + INDIVIDUAL — covers AllowThresholdAdjustment, per-vessel thresholds
Regulation "reg_absolute" {
	Measure = ABSOLUTE
	Scheme = INDIVIDUAL
	Scope = WTW
	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("port_a"), Port("port_b")]
	EmissionsLifetime = 20
	Active = TRUE
	IncludeSlip = TRUE
	IntraFraction = 1.0
	InterFraction = 0.5
	ExtraFraction = 0.0
	RemedialCost = Variable("var_remedial")
	AllowThresholdAdjustment = FALSE
	set_include_vessel("*", TRUE)
	set_global_warming_potential("carbon_dioxide", 1)
	set_global_warming_potential("methane", 25)
	set_fuel_wtt("hfo", "carbon_dioxide", 0.62)
	set_fuel_ttw("hfo", "carbon_dioxide", 3.114)
	set_vessel_threshold("vessel_oil", 5000)
	set_vessel_threshold("vessel_methane", 5000)
	set_vessel_threshold("vessel_methanol", 5000)
	set_vessel_threshold("vessel_ammonia", 5000)
}

# INTENSITY + FLEXIBLE — covers wildcard thresholds, Emissions/Fuels lists
Regulation "reg_intensity" {
	Measure = INTENSITY
	Scheme = FLEXIBLE
	Scope = TTW
	Emissions = Emission("carbon_dioxide")
	Fuels = [Fuel("hfo"), Fuel("lng")]
	Jurisdiction = Port("port_a")
	Active = TRUE
	IncludeSlip = FALSE
	RemedialCost = Forecast("fc_remedial_cost")
	set_include_vessel("*", TRUE)
	set_vessel_threshold("*", Forecast("fc_regulation_threshold"))
	# specific assignment after the wildcard overrides it (declaration order),
	# exercising non-uniform thresholds under a FLEXIBLE scheme
	set_vessel_threshold("vessel_methanol", 60)
}

# TRANSPORT_NOMINAL + INDIVIDUAL — covers set_vessel_capacity
Regulation "reg_transport" {
	Measure = TRANSPORT_NOMINAL
	Scheme = INDIVIDUAL
	Scope = WTW
	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("port_a")]
	Active = TRUE
	RemedialCost = 0
	set_include_vessel("*", TRUE)
	set_vessel_threshold("vessel_oil", 10)
	set_vessel_threshold("vessel_methane", 10)
	set_vessel_threshold("vessel_methanol", 10)
	set_vessel_threshold("vessel_ammonia", 10)
	set_vessel_capacity("vessel_oil", 8000)
	set_vessel_capacity("vessel_methane", 8000)
	set_vessel_capacity("vessel_methanol", 8000)
	set_vessel_capacity("vessel_ammonia", 8000)
}

# PENALTY levy
Levy "levy_penalty" {
	Scheme = PENALTY
	Scope = WTW
	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("port_a")]
	EmissionsLifetime = 20
	Active = TRUE
	IncludeSlip = TRUE
	Level = 50
	LowerThreshold = 0
	UpperThreshold = 100
	set_include_vessel("*", TRUE)
	set_global_warming_potential("methane", 25)
	set_fuel_wtt("lng", "carbon_dioxide", 0.5)
	set_fuel_ttw("lng", "carbon_dioxide", 2.75)
}

# BOTH levy — different scheme
Levy "levy_both" {
	Scheme = BOTH
	Scope = WTW
	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("port_b")]
	Active = TRUE
	Level = 30
	set_include_vessel("*", TRUE)
}
