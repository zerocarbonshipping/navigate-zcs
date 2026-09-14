# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Shared baseline report: wide by default, so small decks maximize regression
# surface. Deck-specific properties are added by re-opening Report "regression"
# in a deck-local include.
#
# Rules:
# - Never add the timing properties (TotalTime, *SolveTime, ...): wall-clock,
#   nondeterministic by construction.
# - One add_*_property call per line: the token validation in
#   tests/attribute/test_report_properties.py only scans single-line calls.
# - Node types absent from a deck produce no CSV for that sheet (and log an
#   expected no-match WARNING per token); baseline file sets are per-deck.
# - Do not request a property no committed deck activates: an all-NaN column
#   compares NaN == NaN and carries zero regression signal (it belongs here
#   only once a deck exercises it).

Report "regression" {
	Directory = "./output/"
	FileFormat = CSV

	add_property(ConsumedEnergy)
	add_property(FuelTypeEnergy)
	add_property(TotalConsumedEnergy)
	add_property(FuelTypeDemand)
	add_property(EquivalentWtt)
	add_property(EquivalentTtw)
	add_property(EquivalentWtw)
	add_property(TotalEquivalentWtw)
	add_property(IntensityTotalEquivalentWtw)
	add_property(FuelExpenses)
	add_property(LevyExpenses)
	add_property(TotalFuelExpenses)
	add_property(TotalLevyExpenses)
	add_property(TotalFuelRelatedExpenses)
	add_property(VesselExpenses)
	add_property(TechnologyExpenses)
	add_property(FuelConversionExpenses)
	add_property(Expenses)
	add_property(VesselTiedCapital)
	add_property(InstalledPower)
	add_property(NewbuildPower)
	add_property(ScrappedPower)
	add_property(FuelConvertedPower)
	add_property(ProductionEnergy)
	add_property(BunkerMass)

	add_fleet_property("*", Trade)
	add_fleet_property("*", ExistingVessels)
	add_fleet_property("*", Scrap)
	add_fleet_property("*", Newbuilds)
	add_fleet_property("*", FuelConversions)
	add_fleet_property("*", VesselExpenses)
	add_fleet_property("*", FuelConversionExpenses)
	add_fleet_property("*", InstalledPower)

	add_vessel_property("*", AssetCharterRate)
	add_vessel_property("*", CargoCharterRate)
	add_vessel_property("*", InvestmentFreightRate)

	add_producer_property("*", Development)
	add_producer_property("*", MaximumDevelopment)
	add_producer_property("*", CumulativeDevelopment)
	add_producer_property("*", FairShareFuelFraction)
	add_producer_property("*", ProductionEnergy)

	add_port_property("*", BunkerPrice)
	add_port_property("*", BunkerMass)
	add_port_property("*", BunkerSupplyMass)

	add_plant_property("*", InvestmentCost)
	add_plant_property("*", InstantaneousCost)

	add_levy_property("*", Collected)
}
