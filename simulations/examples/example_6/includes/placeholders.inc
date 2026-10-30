# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PLACEHOLDERS - every INVENTED or GIVEN number of this case that can be a
# Variable, Curve or Forecast, in one place. Replace them here.
#
# Plain numbers that Navigate takes only as numbers live in their own files:
#   includes/route.inc             distances, speeds, port days, loads   (INVENTED)
#   includes/bunker_logistics.inc  400 nm plant-to-port, 0.03 USD/t/nm   (INVENTED)

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

# ---- feedstock shares (GIVEN by the prompt as this fleet's share) -----------
Variable "rhine_share_used_cooking_oil" {
	Value = 0.02           # GIVEN: this fleet's share of used_cooking_oil_share_shipping
}

Variable "rhine_share_biogenic_carbon_dioxide" {
	Value = 0.02           # GIVEN: this fleet's share of carbon_dioxide_biogenic_share_shipping
}

# ---- Germany's CO2 price (INVENTED), used by includes/co2_price.inc ---------
Forecast "germany_co2_price" {
	# INVENTED: USD per t CO2, 65 in 2026 rising linearly to 150 in 2050
	Table = [
		"01-01-2026"	65
		"01-01-2050"	150
	]
}
