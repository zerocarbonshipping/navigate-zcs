# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PLACEHOLDERS - every INVENTED or GIVEN number of this case that can be a
# Variable, Curve or Forecast, in one place. Replace them here.
#
# Plain numbers that Navigate takes only as numbers live in their own file:
#   includes/route.inc             distances, speeds, port days, loads   (INVENTED)

# ---- fleet (INVENTED) -------------------------------------------------------
Variable "rhine_initial_vessels" {
	Value = 300            # INVENTED: ships in 2026
}

Curve "rhine_age_dist" {
	# INVENTED: ships aged evenly from 0 to 39 years (1/40 each)
	Table = [
		0	0.025
		1	0.025
		2	0.025
		3	0.025
		4	0.025
		5	0.025
		6	0.025
		7	0.025
		8	0.025
		9	0.025
		10	0.025
		11	0.025
		12	0.025
		13	0.025
		14	0.025
		15	0.025
		16	0.025
		17	0.025
		18	0.025
		19	0.025
		20	0.025
		21	0.025
		22	0.025
		23	0.025
		24	0.025
		25	0.025
		26	0.025
		27	0.025
		28	0.025
		29	0.025
		30	0.025
		31	0.025
		32	0.025
		33	0.025
		34	0.025
		35	0.025
		36	0.025
		37	0.025
		38	0.025
		39	0.025
	]
}

Variable "rhine_nominal_capacity" {
	Value = 3000           # INVENTED: t per ship
}

Variable "rhine_lifetime" {
	Value = 40             # INVENTED: years
}

Forecast "rhine_hull_capex" {
	# INVENTED: 6 M USD newbuild price for the hull
	Table = [
		"01-01-2025"	6e6
		"01-01-2050"	6e6
	]
}

Variable "rhine_propulsion_power_capacity" {
	Value = 1.5            # INVENTED: MW
}

Curve "rhine_propulsion_load" {
	# INVENTED: x = knots ; y = MW
	Table = [
		4	0.25
		6	0.6
		8	1.1
		9	1.45
	]
	Extrapolate = LINEAR
}

Variable "rhine_electrical_load_sea" {
	Value = 0.1            # INVENTED: MW
}

Variable "rhine_electrical_load_port" {
	Value = 0.05           # INVENTED: MW
}

Variable "rhine_electrical_power_capacity" {
	Value = 0.2            # INVENTED: MW, generators
}

# ---- handling at the bunker ports (INVENTED) --------------------------------
# USD per t of fuel, storage and the bunkering service, on top of the price
Variable "rhine_handling_fuel_oil" {
	Value = 10             # INVENTED
}

Variable "rhine_handling_lng" {
	Value = 40             # INVENTED: cryogenic storage and bunkering
}

Variable "rhine_handling_fame" {
	Value = 10             # INVENTED
}

Variable "rhine_handling_e_diesel" {
	Value = 10             # INVENTED
}

Variable "rhine_handling_e_methanol" {
	Value = 15             # INVENTED
}

# ---- FAME at the bunker ports (PLACEHOLDERS: replace with your source) -------
# Defaults: what the library's own FAME plant (used cooking oil, grey methanol,
# grid power, in Europe) would cost and emit in this deck, plus 12 USD/t delivery
# to the port. Not net zero: its upstream CO2 falls short of what the engine emits.
Forecast "rhine_fame_price" {
	# USD per t, linear between the points; 45 USD/GJ, nearly flat (37.1 GJ/t)
	Table = [
		"01-01-2026"	1669
		"01-01-2030"	1667
		"01-01-2040"	1663
		"01-01-2050"	1659
	]
}

Forecast "rhine_fame_wtt_carbon_dioxide" {
	# t CO2 per t of fuel, against 2.84 at the tailpipe
	Table = [
		"01-01-2026"	-2.086
		"01-01-2030"	-2.103
		"01-01-2040"	-2.130
		"01-01-2050"	-2.139
	]
}

Variable "rhine_fame_wtt_methane" {
	Value = 0.0016         # t methane per t of fuel
}

# ---- e-fuels at the bunker ports (PLACEHOLDERS: replace with your source) ----
# Defaults: what the library's own plants would cost and emit in this deck
# (alkaline electrolysis in Europe, renewable power, biogenic CO2), plus 12 USD/t
# delivery to the port. Net zero upstream: the CO2 captured equals what the engine
# emits.
Forecast "rhine_e_diesel_price" {
	# USD per t, linear between the points; 103 USD/GJ in 2026, 71 by 2050 (42.7 GJ/t)
	Table = [
		"01-01-2026"	4390
		"01-01-2030"	4023
		"01-01-2040"	3369
		"01-01-2050"	3019
	]
}

Forecast "rhine_e_methanol_price" {
	# USD per t, linear between the points; 84 USD/GJ in 2026, 57 by 2050 (19.9 GJ/t)
	Table = [
		"01-01-2026"	1680
		"01-01-2030"	1512
		"01-01-2040"	1260
		"01-01-2050"	1132
	]
}

Variable "rhine_e_diesel_wtt_carbon_dioxide" {
	Value = -3.206         # t CO2 per t of fuel: minus its tailpipe CO2, net zero
}

Variable "rhine_e_methanol_wtt_carbon_dioxide" {
	Value = -1.38          # t CO2 per t of fuel: minus its tailpipe CO2, net zero
}

# ---- Germany's CO2 price (INVENTED), used by includes/co2_price.inc ---------
Forecast "germany_co2_price" {
	# INVENTED: USD per t CO2, 65 in 2026 rising linearly to 150 in 2050
	Table = [
		"01-01-2026"	65
		"01-01-2050"	150
	]
}
