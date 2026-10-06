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
| ConsumedMass                          | Ton/year                    | Fuel consumed in mass for all fuels.                                                         |
| ConsumedEnergy                        | GJ/year                     | Fuel consumed in energy for all fuels.                                                       |
| ConsumedVolume                        | m<sup>3</sup>/year          | Fuel consumed in volume for all fuels.                                                       |
| FuelTypeMass                          | Ton/year                    | Fuel consumed in mass, aggregated by fuel type.                                              |
| FuelTypeEnergy                        | GJ/year                     | Fuel consumed in energy, aggregated by fuel type.                                            |
| FuelTypeVolume                        | m<sup>3</sup>/year          | Fuel consumed in volume, aggregated by fuel type.                                            |
| TotalConsumedMass                     | Ton/year                    | Total fuel consumed in mass across all fuels.                                                |
| TotalConsumedEnergy                   | GJ/year                     | Total fuel consumed in energy across all fuels.                                              |
| TotalFuelVolume                       | m<sup>3</sup>/year          | Total fuel consumed in volume across all fuels.                                              |
| CumulativeFuelMass                    | Ton/year                    | Cumulative fuel consumed over time in mass for all fuels.                                    |
| CumulativeFuelEnergy                  | GJ/year                     | Cumulative fuel consumed over time in energy for all fuels.                                  |
| CumulativeFuelVolume                  | m<sup>3</sup>/year          | Cumulative fuel consumed over time in volume for all fuels.                                  |
| CumulativeFuelTypeMass                | Ton/year                    | Cumulative fuel consumed over time in mass, aggregated by fuel type.                         |
| CumulativeFuelTypeEnergy              | GJ/year                     | Cumulative fuel consumed over time in energy, aggregated by fuel type.                       |
| CumulativeFuelTypeVolume              | m<sup>3</sup>/year          | Cumulative fuel consumed over time in volume, aggregated by fuel type.                       |
| ConverterMass                         | Ton/year                    | Fuel consumed in mass in vessels of a fuel type across fuels per fuel type.                  |
| ConverterFuelEnergy                   | GJ/year                     | Fuel consumed in energy in vessels of a fuel type across fuels per fuel type.                |
| ConverterFuelVolume                   | m<sup>3</sup>/year          | Fuel consumed in volume in vessels of a fuel type across fuels per fuel type.                |
| ConverterFuelTypeMass                 | Ton/year                    | Fuel consumed in mass in vessels of a fuel type aggregated by fuel type.                     |
| ConverterFuelTypeEnergy               | GJ/year                     | Fuel consumed in energy in vessels of a fuel type aggregated by fuel type.                   |
| ConverterFuelTypeVolume               | m<sup>3</sup>/year          | Fuel consumed in volume in vessels of a fuel type aggregated by fuel type.                   |
| PilotFuelShare                        | Ton/ton                     | The fraction of total fuel spent which is pilot fuel for each vessel fuel type.              |
| WTT                                   | Ton/year                    | Emitted well-to-tank emissions per fuel and emission                                         |
| EquivalentWTT                         | Ton CO<sub>2</sub>-eq./year | Emitted well-to-tank emissions per fuel and emission.                                        |
| TotalEquivalentWTT                    | Ton CO<sub>2</sub>-eq./year | Total emitted well-to-tank emissions.                                                        |
| TTW                                   | Ton/year                    | Emitted tank-to-wake emissions per fuel and emission.                                        |
| EquivalentTTW                         | Ton CO<sub>2</sub>-eq./year | Emitted Tank-to-wake emissions per fuel and emission.                                        |
| TotalEquivalentTTW                    | Ton CO<sub>2</sub>-eq./year | Total emitted tank-to-wake emissions.                                                        |
| WTW                                   | Ton/year                    | Emitted well-to-wake emissions per fuel and emission.                                        |
| EquivalentWTW                         | Ton CO<sub>2</sub>-eq./year | Emitted well-to-wake emissions per fuel and emission.                                        |
| TotalEquivalentWTW                    | Ton CO<sub>2</sub>-eq./year | Total emitted well-to-wake emissions.                                                        |
| CumulativeWTT                         | Ton                         | Cumulative emitted well-to-tank emissions per fuel and emission.                             |
| CumulativeEquivalentWTT               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted well-to-tank emissions per fuel and emission.                             |
| CumulativeTotalEquivalentWTT          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted well-to-tank emissions.                                             |
| CumulativeTTW                         | Ton                         | Cumulative emitted tank-to-wake emissions per fuel and emission.                             |
| CumulativeEquivalentTTW               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted tank-to-wake emissions per fuel and emission.                             |
| CumulativeTotalEquivalentTTW          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted tank-to-wake emissions.                                             |
| CumulativeWTW                         | Ton                         | Cumulative emitted well-to-wake emissions per fuel and emission.                             |
| CumulativeEquivalentWTW               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted well-to-wake emissions per fuel and emission.                             |
| CumulativeTotalEquivalentWTW          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted well-to-wake emissions.                                             |
| IntensityWTT                          | Kg/GJ                       | Emitted well-to-tank emissions per energy per fuel and emission.                             |
| IntensityEquivalentWTT                | Kg CO<sub>2</sub>-eq./GJ    | Emitted well-to-tank emissions per energy per fuel and emission.                             |
| IntensityTotalEquivalentWTT           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted well-to-tank emissions per energy.                                             |
| IntensityTTW                          | Kg/GJ                       | Emitted tank-to-wake emissions per energy per fuel and emission.                             |
| IntensityEquivalentTTW                | Kg CO<sub>2</sub>-eq./GJ    | Emitted tank-to-wake emissions per energy per fuel and emission.                             |
| IntensityTotalEquivalentTTW           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted tank-to-wake emissions per energy.                                             |
| IntensityWTW                          | Kg/GJ                       | Emitted well-to-wake emissions per energy per fuel and emission.                             |
| IntensityEquivalentWTW                | Kg CO<sub>2</sub>-eq./GJ    | Emitted well-to-wake emissions per energy per fuel and emission.                             |
| IntensityTotalEquivalentWTW           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted well-to-wake emissions per energy.                                             |
| CumulativeIntensityWTT                | Kg/GJ                       | Cumulative emitted well-to-tank emissions per energy per fuel and emission.                  |
| CumulativeIntensityEquivalentWTT      | Kg CO<sub>2</sub>-eq./GJ    | Cumulative emitted well-to-tank emissions per energy per fuel and emission.                  |
| CumulativeIntensityTotalEquivalentWTT | Kg CO<sub>2</sub>-eq./GJ    | Cumulative total emitted well-to-tank emissions per energy.                                  |
| CumulativeIntensityTTW                | Kg/GJ                       | Cumulative emitted tank-to-wake emissions per energy per fuel and emission.                  |
| CumulativeIntensityEquivalentTTW      | Kg CO<sub>2</sub>-eq./GJ    | Cumulative emitted tank-to-wake emissions per energy per fuel and emission.                  |
| CumulativeIntensityTotalEquivalentTTW | Kg CO<sub>2</sub>-eq./GJ    | Cumulative total emitted tank-to-wake emissions per energy.                                  |
| CumulativeIntensityWTW                | Kg/GJ                       | Cumulative emitted well-to-wake emissions per energy per fuel and emission.                  |
| CumulativeIntensityEquivalentWTW      | Kg CO<sub>2</sub>-eq./GJ    | Cumulative emitted well-to-wake emissions per energy per fuel and emission.                  |
| CumulativeIntensityTotalEquivalentWTW | Kg CO<sub>2</sub>-eq./GJ    | Cumulative total emitted well-to-wake emissions per energy.                                  |
|  FuelExpenses                         | USD/year                    | Fuel expenses per fuel.                                                                      |
| EmissionExpenses                      | USD/year                    | Emission expenses from permanent storage per fuel.                                           |
| LevyExpenses                          | USD/year                    | Levy expenses per fuel.                                                                      |
| FuelRelatedExpenses                   | USD/year                    | Fuel related expenses (fuel and levy) per fuel.                                              |
| RemedialExpenses                      | USD/year                    | Remedial expenses due to non-compliance with regulations.                                    |
| FlexibilityExpenses                   | USD/year                    | Flexibility expenses due to non-compliance with regulations.                                 |
| SurplusRevenue                        | USD/year                    | Surplus revenue due to over-compliance with regulations.                                     |
| RegulationExpenses                    | USD/year                    | Remedial and flexibility expenses subtracted by surplus revenue from regulations.            |
| TotalFuelExpenses                     | USD/year                    | Total fuel expenses across all fuels.                                                        |
| TotalEmissionExpenses                 | USD/year                    | Total emission expenses across all fuels.                                                    |
| TotalLevyExpenses                     | USD/year                    | Total levy expenses across all fuels.                                                        |
| TotalFuelRelatedExpenses              | USD/year                    | Total fuel related expenses (fuel and levy) across all fuels.                                |
| CumulativeFuelExpenses                | USD                         | Cumulative fuel expenses per fuel.                                                           |
| CumulativeEmissionExpenses            | USD                         | Cumulative emission expenses per fuel.                                                       |
| CumulativeLevyExpenses                | USD                         | Cumulative levy expenses per fuel.                                                           |
| CumulativeFuelRelatedExpenses         | USD                         | Cumulative fuel related expenses (fuel and levy) per fuel                                    |
| CumulativeRemedialExpenses            | USD                         | Cumulative remedial expenses due to non-compliance with regulations.                         |
| CumulativeFlexibilityExpenses         | USD                         | Cumulative flexibility expenses due to non-compliance with regulations.                      |
| CumulativeSurplusRevenue              | USD                         | Cumulative surplus revenue due to over-compliance with regulations.                          |
| CumulativeRegulationExpenses          | USD                         | Cumulative remedial and flexibility expenses subtracted by surplus revenue from regulations. |
| CumulativeTotalFuelExpenses           | USD                         | Cumulative fuel expenses across all fuels.                                                   |
| CumulativeTotalLevyExpenses           | USD                         | Cumulative levy expenses across all fuels.                                                   |
| CumulativeTotalFuelRelatedExpenses    | USD                         | Cumulative fuel related expenses (fuel and levy) across all fuels.                           |

The properties are applicable for the following commands:

* `add_property`
* `add_producer_property`

| **Property name**            | **Unit** | **Description**                                                              |
|------------------------------|  |------------------------------------------------------------------------------|
| CapacityMass                 | Ton/year | Fuel production capacity in mass for all fuels.                              |
| CapacityEnergy               | GJ/year | Fuel production capacity in energy for all fuels.                            |
| CapacityVolume               | m<sup>3</sup>/year | Fuel production capacity in volume for all fuels.                            |
| CapacityTypeMass             | Ton/year | Fuel production capacity in mass, aggregated by fuel type.                   |
| CapacityTypeEnergy           | GJ/year | Fuel production capacity in energy, aggregated by fuel type.                 |
| CapacityTypeVolume           | m<sup>3</sup>/year | Fuel production capacity in volume, aggregated by fuel type.                 |
| CapacityPathMass             | Ton/year | Fuel production capacity in mass, aggregated by fuel path.                   |
| CapacityPathEnergy           | GJ/year | Fuel production capacity in energy, aggregated by fuel path.                 |
| CapacityPathVolume           | m<sup>3</sup>/year | Fuel production capacity in volume, aggregated by fuel path.                 |
| ProductionMass               | Ton/year | Fuel production in mass for all fuels.                                       |
| ProductionEnergy             | GJ/year | Fuel production in energy for all fuels.                                     |
| ProductionVolume             | m<sup>3</sup>/year | Fuel production in volume for all fuels.                                     |
| ProductionTypeMass           | Ton/year | Fuel production in mass, aggregated by fuel type.                            |
| ProductionTypeEnergy         | GJ/year | Fuel production in energy, aggregated by fuel type.                          |
| ProductionTypeVolume         | m<sup>3</sup>/year | Fuel production in volume, aggregated by fuel type.                          |
| ProductionPathMass           | Ton/year | Fuel production in mass, aggregated by fuel path.                            |
| ProductionPathEnergy         | GJ/year | Fuel production in energy, aggregated by fuel path.                          |
| ProductionPathVolume         | m<sup>3</sup>/year | Fuel production in volume, aggregated by fuel path.                          |
| PipelineCapacityMass         | Ton/year | Fuel production capacity in mass in the pipeline for all fuels.              |
| PipelineCapacityEnergy       | GJ/year | Fuel production capacity in energy in the pipeline for all fuels.             |
| PipelineCapacityVolume       | m<sup>3</sup>/year | Fuel production capacity in volume in the pipeline for all fuels.            |
| PipelineCapacityTypeMass     | Ton/year | Fuel production capacity in mass in the pipeline, aggregated by fuel type.   |
| PipelineCapacityTypeEnergy   | GJ/year | Fuel production capacity in energy in the pipeline, aggregated by fuel type. |
| PipelineCapacityTypeVolume   | m<sup>3</sup>/year | Fuel production capacity in volume in the pipeline, aggregated by fuel type. |
| PipelineCapacityPathMass     | Ton/year | Fuel production capacity in mass in the pipeline, aggregated by fuel path.   |
| PipelineCapacityPathEnergy   | GJ/year | Fuel production capacity in energy in the pipeline, aggregated by fuel path. |
| PipelineCapacityPathVolume   | m<sup>3</sup>/year | Fuel production capacity in volume in the pipeline, aggregated by fuel path. |
| PipelineProductionMass       | Ton/year | Fuel production in mass in the pipeline for all fuels.                       |
| PipelineProductionEnergy     | GJ/year | Fuel production in energy in the pipeline for all fuels.                     |
| PipelineProductionVolume     | m<sup>3</sup>/year | Fuel production in volume in the pipeline for all fuels.                     |
| PipelineProductionTypeMass   | Ton/year | Fuel production in mass in the pipeline, aggregated by fuel type.            |
| PipelineProductionTypeEnergy | GJ/year | Fuel production in energy in the pipeline, aggregated by fuel type.          |
| PipelineProductionTypeVolume | m<sup>3</sup>/year | Fuel production in volume in the pipeline, aggregated by fuel type.          |
| PipelineProductionPathMass   | Ton/year | Fuel production in mass in the pipeline, aggregated by fuel path.            |
| PipelineProductionPathEnergy | GJ/year | Fuel production in energy in the pipeline, aggregated by fuel path.          |
| PipelineProductionPathVolume | m<sup>3</sup>/year | Fuel production in volume in the pipeline, aggregated by fuel path.          |
| SourceEnergy                 | MWh/year | Energy used for production per source.                                       |
| FeedstockMass                | Ton/year | Feedstock used in production per feedstock                                   |
| FeedConstraint               | Ton/year | Feed availability constraint per feedstock and process.                      |
| PlantTiedCapital             | USD | Capital tied up in plants (following a linear depreciation schedule).                      |

The properties are applicable for the following commands:

* `add_property`
* `add_port_property`

| **Property name**    | **Unit**           | **Description**                                            |
|----------------------|--------------------|------------------------------------------------------------|
| BunkerMass           | Ton/year           | Fuel bunkered in mass for all fuels.                       |
| BunkerEnergy         | GJ/year            | Fuel bunkered in energy for all fuels.                     |
| BunkerVolume         | m<sup>3</sup>/year | Fuel bunkered in volume for all fuels.                     |
| BunkerSupplyMass     | Ton/year           | Fuel available for bunkering in mass for all fuels.        |
| BunkerSupplyEnergy   | GJ/year            | Fuel available for bunkering in energy for all fuels.      |
| BunkerSupplyVolume   | m<sup>3</sup>/year | Fuel available for bunkering in volume for all fuels.      |
| BunkeringLimitMass   | Ton/year           | Infrastructure limit on bunkering in mass for all fuels.   |
| BunkeringLimitEnergy | GJ/year            | Infrastructure limit on bunkering in energy for all fuels. |
| BunkeringLimitVolume | m<sup>3</sup>/year | Infrastructure limit on bunkering in volume for all fuels. |

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
| AverageAge                         | Year              | Average age of vessels per vessel.                                                              |
| PrimaryScrap                       | # of vessels/year | Number of vessels scrapped due to age per vessel.                                               |
| SecondaryScrap                     | # of vessels/year | Number of vessels scrapped due to trade reduction per vessel.                                   |
| OrderbookNewbuilds                 | # of vessels/year | Number of newbuild vessels based on the orderbook per vessel.                                   |
| InertiaNewbuilds                   | # of vessels/year | Number of newbuild vessels based on fleet inertia per vessel.                                   |
| ModelledNewbuilds                  | # of vessels/year | Number of newbuild vessels based on the modelling per vessel.                                   |
| Scrap                              | # of vessels/year | Number of vessels scrapped (primary and secondary) per vessel.                                  |
| Newbuilds                          | # of vessels/year | Number of newbuild vessels per vessel.                                                          |
| FuelConversions                    | # of vessels/year | Number of vessels fuel converted per vessel to vessel.                                          |
| TechnologyUptake                   | Fraction of fleet | Fraction of vessels with the technology installed per vessel and technology.                    |
| NewbuildTechnologyUptake           | Fraction of fleet | Fraction of newbuild vessels with the technology installed per vessel and technology.           |
| RetrofitTechnologyUptake           | Fraction of fleet | Fraction of vessels retrofitted with the technology per vessel and technology.                  |
| YoungestScrapAge                   | Year              | The youngest scrap age across all vessels.                                                      |
| AverageScrapAge                    | Year              | The average scrap age across all vessels.                                                       |
| ReferenceSpeed                     | Knots             | The average reference (speed defined in Route) speed across all vessels.                        |
| MinimumSpeed                       | Knots             | The average minimum speed attainable across all vessels.                                        |
| MaximumSpeed                       | Knots             | The average maximum speed attainable across all vessels.                                        |
| ActualSpeed                        | Knots             | The average speed across all vessels.                                                           |


The properties are applicable for the following commands:

* `add_producer_property`

| **Property name**               | **Unit**         | **Description**                                                                  |
|---------------------------------|------------------|----------------------------------------------------------------------------------|
| ExistingPlants                  | # of plants      | Number of existing plants per plant.                                             |
| AverageAge                      | Year             | Average age of plants per plant.                                                 |
| Decommissions                   | # of plants/year | Number of plants decommissioned per plant.                                       |
| Newbuilds                       | # of plants/year | Number of newbuild plants per plant.                                             |
| TotalDecommissions              | # of plants/year | Total number of decommissions across all plants.                                 |
| TotalNewbuilds                  | # of plants/year | Total number of newbuilds across all plants.                                     |
| Pipeline                        | # of plants/year | Number of plants in the pipeline per plant.                                      |
| PipelineAdditions               | # of plants/year | Number plants added to the pipeline per plant.                                   |
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
| Voyages                 | #/year                    | Number of voyages.                                                        |
| TimeSea                 | Days/year                 | Time at sea.                                                              |
| TimePort                | Days/year                 | Time in port.                                                             |
| VoyageDuration          | Days/voyage               | Duration of the voyage.                                                   |
| ReferenceSpeed          | Knots                     | Average reference speed (speed defined in Route) of the vessel.           |
| MinimumSpeed            | Knots                     | Average minimum speed attainable.                                         |
| MaximumSpeed            | Knots                     | Average maximum speed attainable.                                         |
| ActualSpeed             | Knots                     | Average actual speed.                                                     |
| Miles                   | Nautical miles/year       | Miles sailed.                                                             |
| CargoMiles              | Cargo-nautical miles/year | Cargo-miles delivered, accounting for loss of cargo-space.                |
| OperationalEnergySaving | GJ/GJ                     | Relative reduction of all energy demand due to operational changes.       |
| TechnologyEnergySaving  | GJ/GJ                     | Relative reduction of all energy demand from added technologies.          |
| EnergySaving            | GJ/GJ                     | Relative reduction of all energy from operational and technology changes. |
| PowerEfficiency         | GJ/GJ                     | Overall thermal efficiency of the power system of the vessel.             |
| SpendEnergySea          | GJ/year                   | Energy spend accounting for thermal efficiency losses at sea.             |
| SpendEnergyPort         | GJ/year                   | Energy spend accounting for thermal efficiency losses in port.            |
| SpendEnergy             | GJ/year                   | Total energy spend accounting for thermal efficiency losses               |
| FuelOPEX                | USD/year                  | Average yearly OPEX for fuel consumption.                                 |
| LevyOPEX                | USD/year                  | Average yearly OPEX for carbon levies.                                    |
| RegulationOPEX          | USD/year                  | Average yearly OPEX for regulations.                                      |
| FuelRelatedOPEX         | USD/year                  | Average yearly OPEX for fuel consumption, carbon levies, and regulations. |
| AssetCharterRate        | USD/year                  | Asset charter rate (owner to operator), does not include fuel expenses.   |
| CargoCharterRate        | USD/year                  | Cargo charter rate (operator to cargo owner), includes fuel expenses.     |
| InvestmentFreightRate   | USD/cargo-nautical mile   | Long-run freight rate at the time of investment.                          |
| InvestmentFreightRate   | USD/cargo-nautical mile   | Long-run freight rate at the actual conditions of the vessel.             |


The properties are applicable for the following commands:

* `add_plant_property`

| **Property name**                        | **Unit**                    | **Description**                                                                 |
|------------------------------------------|-----------------------------|---------------------------------------------------------------------------------|
| Capacity                                 | Ton/year                    | Production capacity.                                                            |
| Production                               | Ton/year                    | Production.                                                                     |
| FeedMass                                 | Ton/ton                     | Ton of feed used per ton of fuel produced.                                      |
| InvestmentCost                           | USD/ton                     | Levelized production cost at time of investment.                                |
| InstantaneousCost                        | USD/ton                     | Supply-weighted average cost over all plants.                                   |
| TTW                                      | Ton/ton                     | Tank-to-wake emissions per ton of fuel per emission.                            |
| EquivalentTTW                            | Ton CO<sub>2</sub>-eq./ton  | Tank-to-wake emissions per ton of fuel per emission.                            |
| TotalEquivalentTTW                       | Ton CO<sub>2</sub>-eq./ton  | Total tank-to-wake emissions per ton of fuel.                                   |
| IntensityTTW                             | Ton/GJ                      | Tank-to-wake emissions per energy in fuel per emission.                         |
| IntensityEquivalentTTW                   | Ton CO<sub>2</sub>-eq./GJ   | Tank-to-wake emissions per energy in fuel per emission.                         |
| IntensityTotalEquivalentTTW              | Ton CO<sub>2</sub>-eq./GJ   | Total tank-to-wake emissions per energy in fuel.                                |
| InvestmentWTT                            | Ton/ton                     | Well-to-tank emissions at time of investment per ton of fuel per emission.      |
| EquivalentInvestmentWTT                  | Ton CO<sub>2</sub>-eq./ton  | Well-to-tank emissions at time of investment per ton of fuel per emission.      |
| TotalEquivalentInvestmentWTT             | Ton CO<sub>2</sub>-eq./ton  | Total well-to-tank emissions at time of investment per ton of fuel.             |
| IntensityInvestmentWTT                   | Ton/GJ                      | Well-to-tank emissions at time of investment per energy in fuel per emission.   |
| IntensityEquivalentInvestmentWTT         | Ton CO<sub>2</sub>-eq./GJ   | Well-to-tank emissions at time of investment per energy in fuel per emission.   |
| IntensityTotalEquivalentInvestmentWTT    | Ton CO<sub>2</sub>-eq./GJ   | Total well-to-tank emissions at time of investment per energy in fuel.          |
| InstantaneousWTT                         | Ton/ton                     | Well-to-tank emissions per ton of fuel per emission.                            |
| EquivalentInstantaneousWTT               | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average well-to-tank emissions per ton of fuel per emission.    |
| TotalEquivalentInstantaneousWTT          | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average total well-to-tank emissions per ton of fuel.           |
| IntensityInstantaneousWTT                | Ton/GJ                      | Supply-weighted average well-to-tank emissions per energy in fuel per emission. |
| IntensityEquivalentInstantaneousWTT      | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average well-to-tank emissions per energy in fuel per emission. |
| IntensityTotalEquivalentInstantaneousWTT | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average total well-to-tank emissions per energy in fuel.        |
| InvestmentWTW                            | Ton/ton                     | Well-to-wake emissions at time of investment per ton of fuel per emission. |
| EquivalentInvestmentWTW                  | Ton CO<sub>2</sub>-eq./ton  | Well-to-wake emissions at time of investment per ton of fuel per emission. |
| TotalEquivalentInvestmentWTW             | Ton CO<sub>2</sub>-eq./ton  | Total well-to-wake emissions at time of investment per ton of fuel. |
| IntensityInvestmentWTW                   | Ton/GJ                      | Well-to-wake emissions at time of investment per energy in fuel per emission. |
| IntensityEquivalentInvestmentWTW         | Ton CO<sub>2</sub>-eq./GJ   | Well-to-wake emissions at time of investment per energy in fuel per emission. |
| IntensityTotalEquivalentInvestmentWTW    | Ton CO<sub>2</sub>-eq./GJ   | Total well-to-wake emissions at time of investment per energy in fuel. |
| InstantaneousWTW                         | Ton/ton                     | Well-to-wake emissions per ton of fuel per emission. |
| EquivalentInstantaneousWTW               | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average well-to-wake emissions per ton of fuel per emission. |
| TotalEquivalentInstantaneousWTW          | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average total well-to-wake emissions per ton of fuel. |
| IntensityInstantaneousWTW                | Ton/GJ                      | Supply-weighted average well-to-wake emissions per energy in fuel per emission. |
| IntensityEquivalentInstantaneousWTW      | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average well-to-wake emissions per energy in fuel per emission. |
| IntensityTotalEquivalentInstantaneousWTW | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average total well-to-wake emissions per energy in fuel. |

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
| SharedThreshold     | Unit\*   | Total allowable emissions measure.                     |
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
| EmissionFactorWTT                         | Ton/ton                    | Well-to-tank emission factor per fuel and emission.                                              |
| EmissionFactorTTW                         | Ton/ton                    | Tank-to-wake emission factor per fuel and emission.                                              |
| EmissionFactorWTW                         | Ton/ton                    | Well-to-wake emission factor per fuel and emission.                                              |
| IntensityEmissionFactorWTT                | Ton/GJ                     | Well-to-tank emission factor per energy in fuel per fuel and emission.                           |
| IntensityEmissionFactorTTW                | Ton/GJ                     | Tank-to-wake emission factor per energy in fuel per fuel and emission.                           |
| IntensityEmissionFactorWTW                | Ton/GJ                     | Well-to-wake emission factor per energy in fuel per fuel and emission.                           |
| EquivalentEmissionFactorWTT               | Ton CO<sub>2</sub>-eq./ton | Well-to-tank equivalent emission factor per fuel and emission.                                   |
| TotalEquivalentEmissionFactorWTT          | Ton CO<sub>2</sub>-eq./ton | Total well-to-tank equivalent emission factor per fuel.                                          |
| EquivalentEmissionFactorTTW               | Ton CO<sub>2</sub>-eq./ton | Tank-to-wake equivalent emission factor per fuel and emission.                                   |
| TotalEquivalentEmissionFactorTTW          | Ton CO<sub>2</sub>-eq./ton | Total tank-to-wake equivalent emission factor per fuel.                                          |
| EquivalentEmissionFactorWTW               | Ton CO<sub>2</sub>-eq./ton | Well-to-wake equivalent emission factor per fuel and emission.                                   |
| TotalEquivalentEmissionFactorWTW          | Ton CO<sub>2</sub>-eq./ton | Total well-to-wake equivalent emission factor per fuel.                                          |
| IntensityEquivalentEmissionFactorWTT      | Ton CO<sub>2</sub>-eq./GJ  | Well-to-tank equivalent emission factor per energy in fuel per fuel and emission.                 |
| IntensityEquivalentEmissionFactorTTW      | Ton CO<sub>2</sub>-eq./GJ  | Tank-to-wake equivalent emission factor per energy in fuel per fuel and emission.                 |
| IntensityEquivalentEmissionFactorWTW      | Ton CO<sub>2</sub>-eq./GJ  | Well-to-wake equivalent emission factor per energy in fuel per fuel and emission.                 |
| IntensityTotalEquivalentEmissionFactorWTT | Ton CO<sub>2</sub>-eq./GJ  | Total well-to-tank equivalent emission factor per energy in fuel.                                |
| IntensityTotalEquivalentEmissionFactorTTW | Ton CO<sub>2</sub>-eq./GJ  | Total tank-to-wake equivalent emission factor per energy in fuel.                                |
| IntensityTotalEquivalentEmissionFactorWTW | Ton CO<sub>2</sub>-eq./GJ  | Total well-to-wake equivalent emission factor per energy in fuel.                                |

\*Depends on the ‘Measure’ of the regulation (ABSOLUTE=ton, INTENSITY=Ton/GJ, TRANSPORT\_NOMINAL=USD/cargo-nautical mile, TRANSPORT=USD/cargo-nautical mile)

The properties are applicable for the following commands:

* `add_levy_property`

| **Property name** | **Unit**  | **Description**                                                        |
|-------------------|-----------|------------------------------------------------------------------------|
| Collected         | USD/year  | Revenue collected or paid out via penalties or subsidies respectively. |
| Level             | USD/ton   | Level of penalty or subsidy.                                           |
| EmissionFactorWTT                         | Ton/ton                    | Well-to-tank emission factor per fuel and emission.                                              |
| EmissionFactorTTW                         | Ton/ton                    | Tank-to-wake emission factor per fuel and emission.                                              |
| EmissionFactorWTW                         | Ton/ton                    | Well-to-wake emission factor per fuel and emission.                                              |
| IntensityEmissionFactorWTT                | Ton/GJ                     | Well-to-tank emission factor per energy in fuel per fuel and emission.                           |
| IntensityEmissionFactorTTW                | Ton/GJ                     | Tank-to-wake emission factor per energy in fuel per fuel and emission.                           |
| IntensityEmissionFactorWTW                | Ton/GJ                     | Well-to-wake emission factor per energy in fuel per fuel and emission.                           |
| EquivalentEmissionFactorWTT               | Ton CO<sub>2</sub>-eq./ton | Well-to-tank equivalent emission factor per fuel and emission.                                   |
| TotalEquivalentEmissionFactorWTT          | Ton CO<sub>2</sub>-eq./ton | Total well-to-tank equivalent emission factor per fuel.                                          |
| EquivalentEmissionFactorTTW               | Ton CO<sub>2</sub>-eq./ton | Tank-to-wake equivalent emission factor per fuel and emission.                                   |
| TotalEquivalentEmissionFactorTTW          | Ton CO<sub>2</sub>-eq./ton | Total tank-to-wake equivalent emission factor per fuel.                                          |
| EquivalentEmissionFactorWTW               | Ton CO<sub>2</sub>-eq./ton | Well-to-wake equivalent emission factor per fuel and emission.                                   |
| TotalEquivalentEmissionFactorWTW          | Ton CO<sub>2</sub>-eq./ton | Total well-to-wake equivalent emission factor per fuel.                                          |
| IntensityEquivalentEmissionFactorWTT      | Ton CO<sub>2</sub>-eq./GJ  | Well-to-tank equivalent emission factor per energy in fuel per fuel and emission.                 |
| IntensityEquivalentEmissionFactorTTW      | Ton CO<sub>2</sub>-eq./GJ  | Tank-to-wake equivalent emission factor per energy in fuel per fuel and emission.                 |
| IntensityEquivalentEmissionFactorWTW      | Ton CO<sub>2</sub>-eq./GJ  | Well-to-wake equivalent emission factor per energy in fuel per fuel and emission.                 |
| IntensityTotalEquivalentEmissionFactorWTT | Ton CO<sub>2</sub>-eq./GJ  | Total well-to-tank equivalent emission factor per energy in fuel.                                |
| IntensityTotalEquivalentEmissionFactorTTW | Ton CO<sub>2</sub>-eq./GJ  | Total tank-to-wake equivalent emission factor per energy in fuel.                                |
| IntensityTotalEquivalentEmissionFactorWTW | Ton CO<sub>2</sub>-eq./GJ  | Total well-to-wake equivalent emission factor per energy in fuel.                                |
