# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Regulation "cii" {

	Measure = TRANSPORT_NOMINAL
	Scheme = INDIVIDUAL

	Scope = TTW
	IncludeSlip = FALSE

	Emissions = Emission("carbon_dioxide")
	Fuels = Fuel("*")

	Jurisdiction = Port("*")

	# a remedial cost of zero means the regulation will have no influence on the decision making.
	# The CII regulation is purely included to track the compliance with the regulation in the output.
	RemedialCost = 0

	# CII only applies to international vessels governed by the IMO
	set_include_vessel("bulk_carrier*international", TRUE)
	set_include_vessel("container*international", TRUE)
	set_include_vessel("tanker*international", TRUE)
	set_include_vessel("cruise*international", TRUE)
	set_include_vessel("ferry*international", TRUE)
	set_include_vessel("gas_carrier*international", TRUE)
	set_include_vessel("general_cargo*international", TRUE)
	set_include_vessel("roro*international", TRUE)

	# assign regulation specific emission factors according to MEPC308(73) for EEDI index
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", 3.114)	# based on HFO
	set_fuel_ttw("liquefied_natural_gas", "carbon_dioxide", 2.75)

	# there was an interim guideline at MEPC80 for how to calculate EF for CII for bio-fuels. This said that:
	# EF = LHV * (1 - p) * 94 if and only if p >= 0.65
	# using the assumption that all our bio-fuels are 0.65> in terms of WTW emissions, then we can assign the Navigate WTW (2030) as the regulation TTW
	set_fuel_ttw("fatty_acid_methyl_ester", "carbon_dioxide", 0.62)	# 84% reduction relative to LSFO, based on EU regulation
	set_fuel_ttw("methane_bio", "carbon_dioxide", 0.043)
	set_fuel_ttw("methanol_bio", "carbon_dioxide", 0.033)
	set_fuel_ttw("ethanol_bio", "carbon_dioxide", 0.03)
	# there are no guidelines for e-fuels, but we assume the same logic as for bio-fuels
	set_fuel_ttw("diesel_electro", "carbon_dioxide", 0.182)
	set_fuel_ttw("methane_electro", "carbon_dioxide", 0.148)
	set_fuel_ttw("methanol_electro", "carbon_dioxide", 0.064)
	set_fuel_ttw("ammonia_electro", "carbon_dioxide", 0.054)

	# there are no guidelines for blue fuels, but we assume the same logic as for bio-fuels
	set_fuel_ttw("ammonia_blue", "carbon_dioxide", 0.344)

	# bulk carrier ------------------------------------------------------------------
	set_vessel_threshold("bulk_carrier_26k_dwt*", Forecast("cii_target_bulk_carrier_26k_dwt"))
	set_vessel_threshold("bulk_carrier_52k_dwt*", Forecast("cii_target_bulk_carrier_52k_dwt"))
	set_vessel_threshold("bulk_carrier_80k_dwt*", Forecast("cii_target_bulk_carrier_80k_dwt"))
	set_vessel_threshold("bulk_carrier_200k_dwt*", Forecast("cii_target_bulk_carrier_200k_dwt"))

	# container ---------------------------------------------------------------------
	set_vessel_threshold("container_1500_teu*", Forecast("cii_target_container_1500_teu"))
	set_vessel_threshold("container_4500_teu*", Forecast("cii_target_container_4500_teu"))
	set_vessel_threshold("container_8000_teu*", Forecast("cii_target_container_8000_teu"))
	set_vessel_threshold("container_15000_teu*", Forecast("cii_target_container_15000_teu"))

	set_vessel_capacity("container_1500_teu*", 22200)
	set_vessel_capacity("container_4500_teu*", 54900)
	set_vessel_capacity("container_8000_teu*", 93000)
	set_vessel_capacity("container_15000_teu*", 160000)

	# tanker ---------------------------------------------------------------------
	set_vessel_threshold("tanker_7500_dwt*", Forecast("cii_target_tanker_7500_dwt"))
	set_vessel_threshold("tanker_47k_dwt*", Forecast("cii_target_tanker_47k_dwt"))
	set_vessel_threshold("tanker_127k_dwt*", Forecast("cii_target_tanker_127k_dwt"))
	set_vessel_threshold("tanker_300k_dwt*", Forecast("cii_target_tanker_300k_dwt"))

	# cruise ---------------------------------------------------------------------
	set_vessel_threshold("cruise_25k_gt*", Forecast("cii_target_cruise_25k_dwt"))
	set_vessel_threshold("cruise_100k_gt*", Forecast("cii_target_cruise_100k_dwt"))
	set_vessel_threshold("cruise_175k_gt*", Forecast("cii_target_cruise_175k_dwt"))

	# ferry ---------------------------------------------------------------------
	set_vessel_threshold("ferry*", Forecast("cii_target_ferry"))

	# gas carrier ---------------------------------------------------------------------
	set_vessel_threshold("gas_carrier_100k_cbm*", Forecast("cii_target_gas_carrier_100k_cbm"))
	set_vessel_capacity("gas_carrier_100k_cbm*", 68000)

	# general cargo ---------------------------------------------------------------------
	set_vessel_threshold("general_cargo*", Forecast("cii_target_general_cargo"))

	# roro ---------------------------------------------------------------------
	set_vessel_threshold("roro_4000_ceu*", Forecast("cii_target_roro_4000_ceu"))
	set_vessel_threshold("roro_7000_ceu*", Forecast("cii_target_roro_7000_ceu"))
	set_vessel_capacity("roro_4000_ceu*", 42500)
	set_vessel_capacity("roro_7000_ceu*", 57700)  # assumed to be 75000 but regulation is capped at 57700
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


Copy Forecast "cii_target_reduction"	"cii_target_bulk_carrier_26k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_bulk_carrier_52k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_bulk_carrier_80k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_bulk_carrier_200k_dwt"

Forecast "cii_target_bulk_carrier_26k_dwt" {
	Multiplier = 8.51
}

Forecast "cii_target_bulk_carrier_52k_dwt" {
	Multiplier = 5.53
}

Forecast "cii_target_bulk_carrier_80k_dwt" {
	Multiplier = 4.23
}

Forecast "cii_target_bulk_carrier_200k_dwt" {
	Multiplier = 2.39
}

Copy Forecast "cii_target_reduction"	"cii_target_container_1500_teu"
Copy Forecast "cii_target_reduction"	"cii_target_container_4500_teu"
Copy Forecast "cii_target_reduction"	"cii_target_container_8000_teu"
Copy Forecast "cii_target_reduction"	"cii_target_container_15000_teu"

Forecast "cii_target_container_1500_teu" {
	Multiplier = 14.87
}

Forecast "cii_target_container_4500_teu" {
	Multiplier = 9.55
}

Forecast "cii_target_container_8000_teu" {
	Multiplier = 7.38
}

Forecast "cii_target_container_15000_teu" {
	Multiplier = 5.66
}

Copy Forecast "cii_target_reduction"	"cii_target_tanker_7500_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_tanker_47k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_tanker_127k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_tanker_300k_dwt"

Forecast "cii_target_tanker_7500_dwt" {
	Multiplier = 22.71
}

Forecast "cii_target_tanker_47k_dwt" {
	Multiplier = 7.41
}

Forecast "cii_target_tanker_127k_dwt" {
	Multiplier = 4.04
}

Forecast "cii_target_tanker_300k_dwt" {
	Multiplier = 2.39
}

Copy Forecast "cii_target_reduction"	"cii_target_cruise_25k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_cruise_100k_dwt"
Copy Forecast "cii_target_reduction"	"cii_target_cruise_175k_dwt"

Forecast "cii_target_cruise_25k_dwt" {
	Multiplier = 19.23
}

Forecast "cii_target_cruise_100k_dwt" {
	Multiplier = 11.31
}

Forecast "cii_target_cruise_175k_dwt" {
	Multiplier = 9.13
}

Copy Forecast "cii_target_reduction"	"cii_target_ferry"

Forecast "cii_target_ferry" {
	Multiplier = 84.33
}

Copy Forecast "cii_target_reduction"	"cii_target_gas_carrier_100k_cbm"

Forecast "cii_target_gas_carrier_100k_cbm" {
	# calculated based on parameters for DWT<65000 if though assumed size is 68000. This is done because the other parameters are quite odd.
	Multiplier = 6.62
}

Copy Forecast "cii_target_reduction"	"cii_target_general_cargo"

Forecast "cii_target_general_cargo" {
	Multiplier = 16.42
}

Copy Forecast "cii_target_reduction"	"cii_target_roro_4000_ceu"
Copy Forecast "cii_target_reduction"	"cii_target_roro_7000_ceu"

Forecast "cii_target_roro_4000_ceu" {
	Multiplier = 6.74
}

Forecast "cii_target_roro_7000_ceu" {
	Multiplier = 4.82
}
