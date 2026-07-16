# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# --------------------------- ENERGY EFFICIENCIES ---------------------------------------
#
# This section specifies the technical measures that can be applied to the 
# Handysize bulk carrier fleet in the Pacific regional scenario. Because we 
# only model one vessel type, all efficiency options are grouped here, allowing 
# easy adjustment of uptake shares and technology combinations. 
#
# Efficiencies include hull, propeller, and operational measures, as well as 
# optional alternative power systems (e.g. Flettner rotors).
#
# Initial shares represent the baseline assumption, while the structure allows 
# users to explore different adoption rates and combinations in sensitivity 
# analyses.
#
# ---------------------------------------------------------------------------------------

Fleet "bulk_carrier_handysize" {
	# technologies
	Technologies = [
		Technology("air_lubrication_bulk_carrier_handy"),
		Technology("exhaust_gas_boiler_ae_bulk_carrier_handy"),
		Technology("flettner_rotor_bulk_carrier_handy"),
		Technology("hull_painting_bulk_carrier_handy"),
		Technology("lighting_system_bulk_carrier_handy"),
		Technology("propeller_improvement_devices_bulk_carrier_handy"),
		Technology("variable_frequency_drive_bulk_carrier_handy")
	]

	set_initial_technology_share("*", "exhaust_gas_boiler_ae_bulk_carrier_handy", Curve("uptake_exhaust_gas_boiler_ae_bulk_carrier_handy"))
	set_initial_technology_share("*", "hull_painting_bulk_carrier_handy", Curve("uptake_hull_painting_bulk_carrier_handy"))
	set_initial_technology_share("*", "lighting_system_bulk_carrier_handy", Curve("uptake_lighting_system_bulk_carrier_handy"))
	set_initial_technology_share("*", "propeller_improvement_devices_bulk_carrier_handy", Curve("uptake_propeller_improvement_devices_bulk_carrier_handy"))
	set_initial_technology_share("*", "variable_frequency_drive_bulk_carrier_handy", Curve("uptake_variable_frequency_drive_bulk_carrier_handy"))
}