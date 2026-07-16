# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Export results to a subfolder called "plots".
# An error is raised if no such folder is found.

Report "report" {

	# Export results to a subfolder called "plots".
	# An error is raised if no such folder is found.
	Directory = "./plots/"
	
		
	# port
	add_port_property("*", BunkerIntensityPrice)				# USD/GJ
	add_port_property("*", BunkerIntensityTotalEquivalentWTT)	# kg / GJ
		
	# fleet
	add_fleet_property("*", TotalEquivalentWTT)		# ton/year
	add_fleet_property("*", TotalEquivalentTTW)		# ton/year
	add_fleet_property("*", TotalEquivalentWTW)		# ton/year
	add_fleet_property("*", TotalConsumedEnergy)	# GJ/year

	# global
	add_property(TotalEquivalentWTT)				# ton/year
	add_property(TotalEquivalentTTW)				# ton/year
	add_property(TotalEquivalentWTW)				# ton/year
	add_property(WTW)								# ton/year
	add_property(TotalConsumedEnergy)				# GJ/year
	add_property(ConsumedEnergy)					# GJ/year
	add_property(InstalledPower)					# MW
	
}
