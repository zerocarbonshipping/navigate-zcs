# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ENERGY EFFICIENCY MEASURES - all seven are the library's own technologies for
# this class, with its own costs and savings. Nothing invented here.

Fleet "copper_trade" {

	Technologies = [
		Technology("exhaust_gas_boiler_ae_bulk_carrier_panamax"),
		Technology("flettner_rotor_bulk_carrier_panamax"),
		Technology("hull_painting_bulk_carrier_panamax"),
		Technology("lighting_system_bulk_carrier_panamax"),
		Technology("propeller_improvement_devices_bulk_carrier_panamax"),
		Technology("variable_frequency_drive_bulk_carrier_panamax"),
		Technology("air_lubrication_bulk_carrier_panamax")
	]

	# Where the world fleet already is, from the library's uptake curves. The
	# Flettner rotor and air lubrication are absent from them, so they start at zero.
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
