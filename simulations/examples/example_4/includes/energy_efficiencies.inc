# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ENERGY EFFICIENCY MEASURES - all six are the library's own technologies for
# this class, with its own costs and savings. Nothing invented here.
#
# The library also offers air lubrication for this class. It is left out: with it
# in, the look-ahead bunkering LP stalls under the "Chilean power x1.4" case in
# Part 4 - a solver problem, not a modelling choice.

Fleet "copper_trade" {

	Technologies = [
		Technology("exhaust_gas_boiler_ae_bulk_carrier_panamax"),
		Technology("flettner_rotor_bulk_carrier_panamax"),
		Technology("hull_painting_bulk_carrier_panamax"),
		Technology("lighting_system_bulk_carrier_panamax"),
		Technology("propeller_improvement_devices_bulk_carrier_panamax"),
		Technology("variable_frequency_drive_bulk_carrier_panamax")
	]

	# Where the world fleet already is, from the library's uptake curves. The
	# Flettner rotor is absent from them, so it starts at zero.
	set_initial_technology_share("*", "exhaust_gas_boiler_ae_bulk_carrier_panamax", Curve("uptake_exhaust_gas_boiler_ae_bulk_carrier_panamax"))
	set_initial_technology_share("*", "hull_painting_bulk_carrier_panamax", Curve("uptake_hull_painting_bulk_carrier_panamax"))
	set_initial_technology_share("*", "lighting_system_bulk_carrier_panamax", Curve("uptake_lighting_system_bulk_carrier_panamax"))
	set_initial_technology_share("*", "propeller_improvement_devices_bulk_carrier_panamax", Curve("uptake_propeller_improvement_devices_bulk_carrier_panamax"))
	set_initial_technology_share("*", "variable_frequency_drive_bulk_carrier_panamax", Curve("uptake_variable_frequency_drive_bulk_carrier_panamax"))

	# Every technology is on offer from the start. Navigate's own default limit of
	# 1 applies, so nothing needs saying here.

	# The library defines no technology-specific rate, so this makes Navigate's
	# own fallback explicit: same value, no warning, nothing invented.
	TechnologyCostOfCapital = Variable("cost_of_capital_vessel")
}
