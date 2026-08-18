# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Report "report_default" {

	Directory = "./plots/"


	# fleets
	add_fleet_property("*", ExistingVessels)
	add_fleet_property("*", Scrap)
	add_fleet_property("*", Newbuilds)
	add_fleet_property("*", FuelConversions)

	# # regulations
	# add_regulation_property("*", SharedThreshold)

	# # levies
	# add_levy_property("*", Collected)

	# manager
	add_property(TotalEquivalentWTT)
	add_property(TotalEquivalentTTW)
	add_property(TotalEquivalentWTW)
	add_property(IntensityTotalEquivalentWTT)
	add_property(IntensityTotalEquivalentTTW)
	add_property(IntensityTotalEquivalentWTW)
	add_property(ConsumedEnergy)
	add_property(InstalledPower)
	add_property(NewbuildPower)
	add_property(FuelConvertedPower, FIRST)
	add_property(TotalFuelExpenses)
	add_property(TotalLevyExpenses)
	add_property(RegulationExpenses)
	add_property(TotalFuelRelatedExpenses)
	add_property(VesselExpenses)
	add_property(FuelConversionExpenses)
	add_property(VesselRelatedExpenses)
	add_property(Expenses)
}