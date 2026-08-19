<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Report

A `Report` node defines a method of extracting results from the simulation. It allows for extraction
of results both on a node basis and on a global basis.

Example:

```python
Report "report_name" {
    add_property(ConsumedEnergy)
    add_port_property("*", BunkerPrice)
    add_vessel_property("*", CAPEX)
}
```

## Attributes

### Directory

This attribute defines the directory in which the report is stored.

* **Data type**: `String`
* Format: Must be a valid directory readable by the Python 'os' module.
* **Default**: Same folder as the `.nav` file

### FileFormat

This attribute sets the file format used to export the report.

* **Data type**: `ID`
* **Legal values**: [FileFormatID](appendix_ids.md#fileformatid)
* **Default**: XLSX

## Commands

### add\_property

This command adds a specified global property to the report.

The parameters are:

* Attribute**:** All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

### add\_fleet\_property

This command adds a specified property of a fleet to the report.

The parameters are:

* Key: Fleet name
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

### add\_vessel\_property

This command adds a specified property of a vessel to the report.

The parameters are:

* Key: Vessel name.
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

### add\_plant\_property

This command adds a specified property of a plant to the report.

The parameters are:

* Key: Plant name
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

### add\_port\_property

This command adds a specified property of a port to the report.

The parameters are:

* Key: Port name
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

### add\_regulation\_property

This command adds a specified property of a regulation to the report.

The parameters are:

* Key: Regulation name
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

### add\_levy\_property

This command adds a specified property of a levy to the report.

The parameters are:

* Key: Levy name
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

## Appendix - Report Node Properties

The properties are applicable for the following commands:

* `add_property`
* `add_fleet_property`
* `add_vessel_property`

| **Property name**                     | **Unit**                    | **Description**                                                                              |
|---------------------------------------|-----------------------------|----------------------------------------------------------------------------------------------|
| RawPropulsionDemandSea                | GJ/year                     | The energy demand for propulsion when at sea excluding technologies.                         |
| RawElectricalDemandSea                | GJ/year                     | The energy demand for electricity when at sea excluding technologies.                        |
| RawHeatDemandSea                      | GJ/year                     | The energy demand for heat when at sea excluding technologies.                               |
| RawElectricalDemandPort               | GJ/year                     | The energy demand for electricity when in port excluding technologies.                       |
| RawHeatDemandPort                     | GJ/year                     | The energy demand for heat when in port excluding technologies.                              |
| RawPropulsionDemand                   | GJ/year                     | The energy demand for propulsion excluding technologies.                                     |
| RawElectricalDemand                   | GJ/year                     | The energy demand for electricity excluding technologies.                                    |
| RawHeatDemand                         | GJ/year                     | The energy demand for heat excluding technologies.                                           |
| RawDemandSea                          | GJ/year                     | The energy demand for everything at sea excluding technologies.                              |
| RawDemandPort                         | GJ/year                     | The energy demand for everything in port excluding technologies.                             |
| RawDemand                             | GJ/year                     | The total energy demand excluding technologies.                                              |
| PropulsionDemandSea                   | GJ/year                     | The energy demand for propulsion when at sea.                                                |
| ElectricalDemandSea                   | GJ/year                     | The energy demand for electricity when at sea.                                               |
| HeatDemandSea                         | GJ/year                     | The energy demand for heat when at sea.                                                      |
| ElectricalDemandPort                  | GJ/year                     | The energy demand for electricity when in port.                                              |
| HeatDemandPort                        | GJ/year                     | The energy demand for heat when in port.                                                     |
| PropulsionDemand                      | GJ/year                     | The energy demand for propulsion.                                                            |
| ElectricalDemand                      | GJ/year                     | The energy demand for electrical.                                                            |
| HeatDemand                            | GJ/year                     | The energy demand for heat.                                                                  |
| DemandSea                             | GJ/year                     | The energy demand at sea.                                                                    |
| DemandPort                            | GJ/year                     | The energy demand in port.                                                                   |
| Demand                                | GJ/year                     | The energy demand.                                                                           |
| ConsumedEnergy                        | GJ/year                     | Fuel consumed in energy for all fuels.                                                       |
| FuelTypeEnergy                        | GJ/year                     | Fuel consumed in energy, aggregated by fuel type.                                            |
| TotalConsumedEnergy                   | GJ/year                     | Total consumed energy across all fuels plus shore power.                                     |
| ShorePowerEnergy                      | GJ/year                     | Shore power energy supplied.                                                                 |
| ConverterFuelEnergy                   | GJ/year                     | Fuel consumed in energy in vessels of a fuel type across fuels per fuel type.                |
| PilotFuelShare                        | Ton/ton                     | The fraction of total fuel spent which is pilot fuel for each vessel fuel type.              |
| EquivalentWTT                         | Ton CO<sub>2</sub>-eq./year | Emitted well-to-tank emissions per fuel and emission.                                        |
| TotalEquivalentWTT                    | Ton CO<sub>2</sub>-eq./year | Total emitted well-to-tank emissions.                                                        |
| EquivalentTTW                         | Ton CO<sub>2</sub>-eq./year | Emitted Tank-to-wake emissions per fuel and emission.                                        |
| TotalEquivalentTTW                    | Ton CO<sub>2</sub>-eq./year | Total emitted tank-to-wake emissions.                                                        |
| EquivalentWTW                         | Ton CO<sub>2</sub>-eq./year | Emitted well-to-wake emissions per fuel and emission.                                        |
| TotalEquivalentWTW                    | Ton CO<sub>2</sub>-eq./year | Total emitted well-to-wake emissions across all fuels plus shore power.                      |
| ShorePowerEmission                    | Ton/year                    | Shore power emission per emission (well-to-wake lump, no WTT/TTW split).                     |
| CumulativeEquivalentWTT               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted well-to-tank emissions per fuel and emission.                             |
| CumulativeTotalEquivalentWTT          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted well-to-tank emissions.                                             |
| CumulativeEquivalentTTW               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted tank-to-wake emissions per fuel and emission.                             |
| CumulativeTotalEquivalentTTW          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted tank-to-wake emissions.                                             |
| CumulativeEquivalentWTW               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted well-to-wake emissions per fuel and emission.                             |
| CumulativeTotalEquivalentWTW          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted well-to-wake emissions, including shore power.                      |
| IntensityEquivalentWTT                | Kg CO<sub>2</sub>-eq./GJ    | Emitted well-to-tank emissions per energy per fuel and emission.                             |
| IntensityTotalEquivalentWTT           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted well-to-tank emissions per total consumed energy (including shore power).      |
| IntensityEquivalentTTW                | Kg CO<sub>2</sub>-eq./GJ    | Emitted tank-to-wake emissions per energy per fuel and emission.                             |
| IntensityTotalEquivalentTTW           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted tank-to-wake emissions per total consumed energy (including shore power).      |
| IntensityEquivalentWTW                | Kg CO<sub>2</sub>-eq./GJ    | Emitted well-to-wake emissions per energy per fuel and emission.                             |
| IntensityTotalEquivalentWTW           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted well-to-wake emissions per energy, including shore power.                      |
|  FuelExpenses                         | USD/year                    | Fuel expenses per fuel.                                                                      |
| LevyExpenses                          | USD/year                    | Levy expenses per fuel.                                                                      |
| FuelRelatedExpenses                   | USD/year                    | Fuel related expenses (fuel and levy) per fuel.                                              |
| RemedialExpenses                      | USD/year                    | Remedial expenses due to non-compliance with regulations.                                    |
| FlexibilityExpenses                   | USD/year                    | Flexibility expenses due to non-compliance with regulations.                                 |
| SurplusRevenue                        | USD/year                    | Surplus revenue due to over-compliance with regulations.                                     |
| RegulationExpenses                    | USD/year                    | Remedial and flexibility expenses subtracted by surplus revenue from regulations.            |
| TotalFuelExpenses                     | USD/year                    | Total fuel expenses across all fuels plus shore power.                                       |
| ShorePowerExpenses                    | USD/year                    | Shore power purchase cost.                                                                   |
| TotalLevyExpenses                     | USD/year                    | Total levy expenses across all fuels.                                                        |
| TotalFuelRelatedExpenses              | USD/year                    | Total fuel related expenses (fuel expenses including shore power, plus levy expenses).       |
| CumulativeFuelExpenses                | USD                         | Cumulative fuel expenses per fuel.                                                           |
| CumulativeLevyExpenses                | USD                         | Cumulative levy expenses per fuel.                                                           |
| CumulativeFuelRelatedExpenses         | USD                         | Cumulative fuel related expenses (fuel and levy) per fuel                                    |
| CumulativeRemedialExpenses            | USD                         | Cumulative remedial expenses due to non-compliance with regulations.                         |
| CumulativeFlexibilityExpenses         | USD                         | Cumulative flexibility expenses due to non-compliance with regulations.                      |
| CumulativeSurplusRevenue              | USD                         | Cumulative surplus revenue due to over-compliance with regulations.                          |
| CumulativeRegulationExpenses          | USD                         | Cumulative remedial and flexibility expenses subtracted by surplus revenue from regulations. |
| CumulativeTotalFuelExpenses           | USD                         | Cumulative fuel expenses across all fuels plus shore power.                                  |
| CumulativeTotalLevyExpenses           | USD                         | Cumulative levy expenses across all fuels.                                                   |
| CumulativeTotalFuelRelatedExpenses    | USD                         | Cumulative fuel related expenses (fuel and levy) across all fuels plus shore power.          |

The properties are applicable for the following commands:

* `add_property`
* `add_producer_property`

| **Property name**            | **Unit** | **Description**                                                              |
|------------------------------|  |------------------------------------------------------------------------------|
| ProductionEnergy             | GJ/year | Fuel production in energy for all fuels.                                     |
| ProductionTypeEnergy         | GJ/year | Fuel production in energy, aggregated by fuel type.                          |
| FeedMass                     | Ton/year | Feed used in production per feedstock and process.                           |
| FeedConstraint               | Ton/year | Feed availability constraint per feedstock and process.                      |
| PlantTiedCapital             | USD | Capital tied up in plants (following a linear depreciation schedule).                      |

The properties are applicable for the following commands:

* `add_property`
* `add_port_property`

| **Property name**    | **Unit**           | **Description**                                            |
|----------------------|--------------------|------------------------------------------------------------|
| BunkerMass           | Ton/year           | Fuel bunkered in mass for all fuels.                       |
| BunkerEnergy         | GJ/year            | Fuel bunkered in energy for all fuels.                     |
| BunkerSupplyMass     | Ton/year           | Fuel available for bunkering in mass for all fuels.        |
| BunkerSupplyEnergy   | GJ/year            | Fuel available for bunkering in energy for all fuels.      |
| BunkeringLimitMass   | Ton/year           | Infrastructure limit on bunkering in mass for all fuels.   |
| BunkeringLimitEnergy | GJ/year            | Infrastructure limit on bunkering in energy for all fuels. |

The properties are applicable for the following commands:

* `add_property`
* `add_fleet_property`

| **Property name**                     | **Unit** | **Description**                                                        |
|---------------------------------------|----------|------------------------------------------------------------------------|
| PropulsionSaving                      | GJ/GJ    | Relative reduction of propulsion energy demand.                        |
| ElectricalSaving                      | GJ/GJ    | Relative reduction of electrical energy demand.                        |
| HeatSaving                            | GJ/GJ    | Relative reduction of heat energy demand.                              |
| OperationalEnergySaving               | GJ/GJ    | Relative reduction of energy from operational measures.                |
| TechnologyEnergySaving                | GJ/GJ    | Relative reduction of energy from added technologies.                  |
| EnergySaving                          | GJ/GJ    | Relative reduction of all energy demand.                               |
| InstalledPower                        | MW       | Installed power per fuel type.                                         |
| NewbuildPower                         | MW/year  | Installed power for newbuilds per fuel type.                           |
| ScrappedPower                         | MW/year  | Installed power scrapped per fuel type.                                |
| FuelConvertedPower                    | MW/year  | Installed power fuel converted per fuel type to fuel type.             |
| CumulativeNewbuildPower               | MW       | Cumulative installed power for newbuilds per fuel type.                |
| CumulativeScrappedPopwer              | MW       | Cumulative installed power scrapped per fuel type.                     |
| CumulativeFuelConvertedPower          | MW       | Cumulative installed power fuel converted per fuel type to fuel type.  |
| VesselExpenses                        | USD/year | Running expenses of acquisition of all vessels.                        |
| TechnologyNewbuildExpenses            | USD/year | Running expenses of technologies for all newbuilds.                    |
| TechnologyRetrofitExpenses            | USD/year | Running expenses of technologies for all retrofits.                    |
| FuelConversionExpenses                | USD/year | Running expenses of all fuel conversions.                              |
| VesselRelatedExpenses                 | USD/year | Running expenses of all vessels.                                       |
| Expenses                              | USD/year | Running expenses including fuel of all vessels.                        |
| CumulativeVesselExpenses              | USD      | Cumulative running expenses of acquisition of all vessels.             |
| CumulativeTechnologyNewbuildExpenses  | USD      | Cumulative running expenses of technologies for all newbuilds.         |
| CumulativeTechnologyRetrofitExpenses  | USD      | Cumulative running expenses of technologies for all retrofits.         |
| CumulativeFuelConversionExpenses      | USD      | Cumulative running expenses of fuel conversions for all newbuilds.     |
| CumulativeVesselRelatedExpenses       | USD      | Cumulative running expenses of all vessels.                            |
| CumulativeExpenses                    | USD      | Cumulative running expenses including fuel of all vessels.             |
| VesselTiedCapital                     | USD      | Capital tied up in vessels (following a linear depreciation schedule). |
| FuelTypeDemand                        | GJ/year  | Demand for fuel if using minimum pilot fuel share per fuel type.       |

The properties are applicable for the following commands:

* `add_property`

| **Property name**    | **Unit** | **Description**                                                                  |
|----------------------| --- |---------------------------------------------------------------------------------------|
| TotalTime            | Second | Total simulation time.                                                             |
| ExpectedBuildTime    | Second | The LP build time for the expected future bunker decisions.                        |
| ExpectedSolveTime    | Second | The LP solve time for the expected future bunker decisions.                        |
| ExpectedTransferTime | Second | The transfer time for the results of the expected future bunker decisions.         |
| SpeedTime            | Second | The time spent running the speed management algorithm.                             |
| RetrofitTime         | Second | The time spent running the technology retrofit algorithm                           |
| EvolutionTime        | Second | The time spent calculating the evolution of the producer and fleet nodes.          |
| ExistingBuildTime    | Second | The LP build time for the existing bunker decision.                                |
| ExistingSolveTime    | Second | The LP solve time for the existing bunker decision.                                |
| ExistingTransferTime | Second | The transfer time for the results of the existing bunker decision.                 |
| OtherTime            | Second | The time spent on other relevant calculations such as calculation of expectations. |

The properties are applicable for the following commands:

* `add_fleet_property`

| **Property name**                  | **Unit**          | **Description**                                                                                 |
|------------------------------------|-------------------|-------------------------------------------------------------------------------------------------|
| Trade                              | Cargo-miles/year  | Trade satisfied.                                                                                |
| ExistingVessels                    | # of vessels      | Number of existing vessels per vessel.                                                          |
| Scrap                              | # of vessels/year | Number of vessels scrapped (primary and secondary) per vessel.                                  |
| Newbuilds                          | # of vessels/year | Number of newbuild vessels per vessel.                                                          |
| FuelConversions                    | # of vessels/year | Number of vessels fuel converted per vessel to vessel.                                          |
| TechnologyUptake                   | Fraction of fleet | Fraction of vessels with the technology installed per vessel and technology.                    |
| NewbuildTechnologyUptake           | Fraction of fleet | Fraction of newbuild vessels with the technology installed per vessel and technology.           |
| RetrofitTechnologyUptake           | Fraction of fleet | Fraction of vessels retrofitted with the technology per vessel and technology.                  |
| ReferenceSpeed                     | Knots             | The average reference (speed defined in Route) speed across all vessels.                        |
| MinimumSpeed                       | Knots             | The average minimum speed attainable across all vessels.                                        |
| MaximumSpeed                       | Knots             | The average maximum speed attainable across all vessels.                                        |
| ActualSpeed                        | Knots             | The average speed across all vessels.                                                           |


The properties are applicable for the following commands:

* `add_producer_property`

| **Property name**               | **Unit**         | **Description**                                                                  |
|---------------------------------|------------------|----------------------------------------------------------------------------------|
| DevelopmentConstraint           | # of plants/year | Number of plants that can be added to the pipeline across all plants.            |
| Development                     | # of plants/year | Number of plants added to the pipeline across all plants.                        |
| CumulativeDevelopmentConstraint | # of plants      | Cumulative number of plants that can be added to the pipeline across all plants. |
| CumulativeDevelopment           | # of plants      | Cumulative number of plants added to the pipeline across all plants.             |
| FairShareFuelFraction           | Fraction         | Fraction of fuel demand allocated to the producer to supply.                     |

The properties are applicable for the following commands:

* `add_vessel_property`

| **Property name**       | **Unit**                  | **Description**                                                           |
|-------------------------|---------------------------|---------------------------------------------------------------------------|
| Lifetime                | Year                      | Lifetime of the vessel.                                                   |
| ReferenceSpeed          | Knots                     | Average reference speed (speed defined in Route) of the vessel.           |
| MinimumSpeed            | Knots                     | Average minimum speed attainable.                                         |
| MaximumSpeed            | Knots                     | Average maximum speed attainable.                                         |
| ActualSpeed             | Knots                     | Average actual speed.                                                     |
| OperationalEnergySaving | GJ/GJ                     | Relative reduction of all energy demand due to operational changes.       |
| TechnologyEnergySaving  | GJ/GJ                     | Relative reduction of all energy demand from added technologies.          |
| EnergySaving            | GJ/GJ                     | Relative reduction of all energy from operational and technology changes. |
| AssetCharterRate        | USD/year                  | Asset charter rate (owner to operator), does not include fuel expenses.   |
| CargoCharterRate        | USD/year                  | Cargo charter rate (operator to cargo owner), includes fuel expenses.     |
| InvestmentFreightRate   | USD/cargo-nautical mile   | Long-run freight rate at the time of investment.                          |
| InvestmentFreightRate   | USD/cargo-nautical mile   | Long-run freight rate at the actual conditions of the vessel.             |


The properties are applicable for the following commands:

* `add_plant_property`

| **Property name**                        | **Unit**                    | **Description**                                                                 |
|------------------------------------------|-----------------------------|---------------------------------------------------------------------------------|
| InvestmentCost                           | USD/ton                     | Levelized production cost at time of investment.                                |
| InstantaneousCost                        | USD/ton                     | Supply-weighted average cost over all plants.                                   |
| EquivalentInvestmentWTT                  | Ton CO<sub>2</sub>-eq./ton  | Well-to-tank emissions at time of investment per ton of fuel per emission.      |
| TotalEquivalentInvestmentWTT             | Ton CO<sub>2</sub>-eq./ton  | Total well-to-tank emissions at time of investment per ton of fuel.             |
| IntensityEquivalentInvestmentWTT         | Ton CO<sub>2</sub>-eq./GJ   | Well-to-tank emissions at time of investment per energy in fuel per emission.   |
| IntensityTotalEquivalentInvestmentWTT    | Ton CO<sub>2</sub>-eq./GJ   | Total well-to-tank emissions at time of investment per energy in fuel.          |
| EquivalentInstantaneousWTT               | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average well-to-tank emissions per ton of fuel per emission.    |
| TotalEquivalentInstantaneousWTT          | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average total well-to-tank emissions per ton of fuel.           |
| IntensityEquivalentInstantaneousWTT      | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average well-to-tank emissions per energy in fuel per emission. |
| IntensityTotalEquivalentInstantaneousWTT | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average total well-to-tank emissions per energy in fuel.        |

The properties are applicable for the following commands:

* `add_port_property`

| **Property name**                 | **Unit**                   | **Description**                                                                 |
|-----------------------------------|----------------------------|---------------------------------------------------------------------------------|
| BunkerPrice                       | USD/ton                    | Bunker price per ton of fuel.                                                   |
| BunkerIntensityPrice              | USD/GJ                     | Bunker price per energy in fuel.                                                |
| BunkerWTT                         | Ton/ton                    | Well-to-tank emissions of bunker fuel per ton of fuel per fuel and emission.    |
| BunkerEquivalentWTT               | Ton CO<sub>2</sub>-eq./ton | Well-to-tank emissions of bunker fuel per ton of fuel per fuel and emission.    |
| BunkerTotalEquivalentWTT          | Ton CO<sub>2</sub>-eq./ton | Well-to-tank emissions of bunker fuel per ton of fuel per fuel.                 |
| BunkerIntensityWTT                | Ton/GJ                     | Well-to-tank emissions of bunker fuel per energy in fuel per fuel and emission. |
| BunkerIntensityEquivalentWTT      | Ton CO<sub>2</sub>-eq./GJ  | Well-to-tank emissions of bunker fuel per energy in fuel per fuel and emission. |
| BunkerIntensityTotalEquivalentWTT | Ton CO<sub>2</sub>-eq./GJ  | Well-to-tank emissions of bunker fuel per energy in per fuel.                   |

The properties are applicable for the following commands:

* `add_regulation_property`

| **Property name**   | **Unit** | **Description**                                        |
|---------------------|----------|--------------------------------------------------------|
| FlexibilityCost     | USD/ton  | Cost of flexibility compliance unit.                   |
| RemedialCost        | USD/ton  | Cost of remedial compliance unit.                      |
| VesselTreshold      | Unit\*   | Allowable emissions measure per vessel.                |
| SharedThreshold     | Unit\*   | Fleet-level effective target of a FLEXIBLE regulation. |
| VesselCompliance    | Unit\*   | Achieved emissions measure per vessel.                 |
| SharedCompliance    | Unit\*   | Total achieved emissions measure.                      |
| IntendedUnits       | Ton      | Total intended units.                                  |
| AchievedUnits       | Ton      | Total achieved units.                                  |
| SurplusUnits        | Ton      | Surplus compliance units generated.                    |
| FlexibilityUnits    | Ton      | Flexibility compliance units used.                     |
| RemedialUnits       | Ton      | Remedial compliance units required.                    |
| SurplusRevenue      | USD/ton  | Revenue from selling surplus compliance units.         |
| FlexibilityExpenses | USD/ton  | Expenses from purchasing flexibility compliance units. |
| RemedialExpenses    | USD/ton  | Expenses from purchasing remedial compliance units.    |

\*Depends on the ‘Measure’ of the regulation (ABSOLUTE=ton, INTENSITY=Ton/GJ, TRANSPORT\_NOMINAL=USD/cargo-nautical mile, TRANSPORT=USD/cargo-nautical mile)

The properties are applicable for the following commands:

* `add_levy_property`

| **Property name** | **Unit**  | **Description**                                                        |
|-------------------|-----------|------------------------------------------------------------------------|
| Collected         | USD/year  | Revenue collected or paid out via penalties or subsidies respectively. |
