# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------ CARBON INTENSITY INDICATOR ---------------------------
#
# Tracks compliance of international container ships with IMO’s CII rule 
# based on CO₂ per transport work (TTW). Used here for monitoring only, 
# with no effect on decision-making (remedial cost = 0).
#
# -----------------------------------------------------------------------

Regulation "cii" {

	Measure = TRANSPORT_NOMINAL
	Scheme = INDIVIDUAL

	Scope = TTW
	IncludeSlip = FALSE

	Emissions = Emission("carbon_dioxide")
	Fuels = Fuel("*")
	
	Jurisdiction = [Port("singapore"), Port("rotterdam"), Port("hamburg"), Port("aalborg")]
	
	# A remedial cost of zero means the regulation will have no influence on the decision making.
	# The CII regulation is purely included to track the compliance with the regulation in the output.
	RemedialCost = 0
	
	# CII applies to all vessels in this scenario
	set_include_vessel("*", TRUE)
	
	# assign regulation specific emission factors according to MEPC308(73) for EEDI index
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", 3.114)

	# there was an interim guideline at MEPC80 for how to calculate EF for CII for bio-fuels. This said that:
	# EF = LHV * (1 - p) * 94 if and only if p >= 0.65
	# using the assumption that all our bio-fuels are 0.65> in terms of WTW emissions, then we can assign the Navigate WTW (2030) as the regulation TTW
	set_fuel_ttw("methanol_bio", "carbon_dioxide", 0.3)

	set_vessel_threshold("feeder_*", Forecast("cii_target_container_1500_teu"))
	set_vessel_threshold("mainline_*", Forecast("cii_target_container_15000_teu"))
	
	set_vessel_capacity("feeder_*", 22000)
	set_vessel_capacity("mainline_*", 160000)
}

Forecast "cii_target_reduction" {
	Table = [
		"01-01-2019"	1.0
		"01-01-2020"	0.99
		"01-01-2021"	0.98
		"01-01-2022"	0.97
		"01-01-2023"	0.95
		"01-01-2024"	0.93
		"01-01-2025"	0.91
		"01-01-2026"	0.89
		"01-01-2027"	0.87
		"01-01-2028"	0.85
		"01-01-2029"	0.83
		"01-01-2030"	0.81
	]
	
	Extrapolate = FLAT
}

Copy Forecast "cii_target_reduction"	"cii_target_container_1500_teu"
Copy Forecast "cii_target_reduction"	"cii_target_container_15000_teu"

Forecast "cii_target_container_1500_teu" {
	Multiplier = 14.93
}

Forecast "cii_target_container_15000_teu" {
	Multiplier = 5.66
}
