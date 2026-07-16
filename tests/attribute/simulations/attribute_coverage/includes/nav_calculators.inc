# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Calculator nodes: Forecast, Curve, Surface, Timetable, Variable
#
# Attributes covered:
#   Forecast/Curve: Interpolate, Extrapolate, Below, Above,
#                   Addition, Multiplier, LowerBound, UpperBound
#   Surface:        Interpolate, Extrapolate, Outside,
#                   Addition, Multiplier, LowerBound, UpperBound
#   Timetable:      Interpolate, Extrapolate, Outside,
#                   Addition, Multiplier, LowerBound, UpperBound
#   Variable:       Value, Addition, Multiplier, LowerBound, UpperBound

# --- Forecasts ---------------------------------------------------------------

Forecast "fc_trade_growth" {
	Table = [
		"01-01-2025"	0.03
		"01-01-2030"	0.04
		"01-01-2035"	0.05
	]
	Interpolate = LINEAR
	Extrapolate = FLAT
	Below = 0.01
	Above = 0.10
	Addition = 0
	Multiplier = 1
	LowerBound = 0
	UpperBound = 1
}

Forecast "fc_orderbook_a" {
	Table = [
		"01-01-2025"	0
		"01-01-2030"	2
		"01-01-2035"	5
	]
	Extrapolate = FLAT
}

Forecast "fc_orderbook_b" {
	Table = [
		"01-01-2025"	0
		"01-01-2035"	3
	]
	Extrapolate = FLAT
}

Forecast "fc_pipeline" {
	Table = [
		"01-01-2025"	0
		"01-01-2030"	500
		"01-01-2035"	1500
	]
	Extrapolate = LINEAR
}

Forecast "fc_regulation_threshold" {
	Table = [
		"01-01-2025"	20
		"01-01-2030"	15
		"01-01-2035"	10
	]
	Extrapolate = FLAT
}

Forecast "fc_remedial_cost" {
	Table = [
		"01-01-2025"	50
		"01-01-2030"	100
	]
	Extrapolate = FLAT
}

Forecast "fc_operational_saving" {
	Table = [
		"01-01-2025"	0.02
		"01-01-2035"	0.05
	]
	Extrapolate = FLAT
}

# --- Curves ------------------------------------------------------------------

Curve "curve_age_a" {
	Table = [
		0	0.10
		3	0.30
		6	0.30
		9	0.20
		12	0.10
	]
	Interpolate = LINEAR
	Extrapolate = FLAT
	Below = 0
	Above = 0
}

Curve "curve_age_b" {
	Table = [
		0	0.5
		5	0.5
	]
	Interpolate = PREVIOUS
	Extrapolate = FLAT
	Below = 0
	Above = 0
}

Curve "curve_tech_uptake" {
	Table = [
		0	0.0
		10	0.5
		25	1.0
	]
	Interpolate = LINEAR
	Extrapolate = FLAT
	Below = 0
	Above = 1
	Addition = 0
	Multiplier = 1
	LowerBound = 0
	UpperBound = 1
}

Curve "curve_plant_age" {
	Table = [
		0	0.5
		5	0.5
	]
	Extrapolate = FLAT
}

# --- Surface -----------------------------------------------------------------

Surface "surface_load" {
	Table = [
		0	1
		6.5	0.54	0.76
		10.5	1.64	2.30
		14.5	4.20	5.91
	]
	Interpolate = LINEAR
	Extrapolate = FLAT
	Outside = 0
	Addition = 0
	Multiplier = 1
	LowerBound = 0
	UpperBound = INF
}

# --- Timetable ---------------------------------------------------------------

Timetable "timetable_cost" {
	Table = [
		10	20
		"01-01-2025"	100	200
		"01-01-2030"	150	250
		"01-01-2035"	200	300
	]
	Interpolate = LINEAR
	Extrapolate = FLAT
	Outside = 0
	Addition = 0
	Multiplier = 1
	LowerBound = 0
	UpperBound = INF
}

# --- Variables ---------------------------------------------------------------

Variable "var_efficiency" {
	Value = 0.50
	Addition = 0
	Multiplier = 1
	LowerBound = 0
	UpperBound = 1
}

Variable "var_shore_transfer" {
	Value = 0.5
}

Variable "var_remedial" {
	Value = 100
}
