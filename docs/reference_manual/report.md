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
    add_vessel_property("*", AssetCharterRate)
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

### add\_producer\_property

This command adds a specified property of a producer to the report.

The parameters are:

* Key: Producer name
* Attribute: All allowed attributes are listed in the [Report Properties](#appendix---report-node-properties) section.
* Reduce: Reduction axis; see [ReportReduceID](appendix_ids.md#reportreduceid). Default: None (no reduction).

## Appendix - Report Node Properties

The properties are applicable for the following commands:

* `add_property`
* `add_fleet_property`
* `add_vessel_property`

| **Property name**                     | **Unit**                    | **Description**                                                                              |
|---------------------------------------|-----------------------------|----------------------------------------------------------------------------------------------|
| RawEnergySea                          | GJ/year                     | The energy demand at sea before operational measures and technologies, one column per energy demand type. |
| RawEnergyPort                         | GJ/year                     | The energy demand in port before operational measures and technologies, one column per energy demand type in port (electrical and heat). |
| RawEnergy                             | GJ/year                     | The total energy demand at sea and in port before operational measures and technologies.     |
| OperationalEnergySea                  | GJ/year                     | The energy demand at sea after operational measures and before technologies, one column per energy demand type. |
| OperationalEnergyPort                 | GJ/year                     | The energy demand in port after operational measures and before technologies, one column per energy demand type in port (electrical and heat). |
| OperationalEnergy                     | GJ/year                     | The total energy demand at sea and in port after operational measures and before technologies. |
| EnergySea                             | GJ/year                     | The energy demand at sea after operational measures and technologies, one column per energy demand type. |
| EnergyPort                            | GJ/year                     | The energy demand in port after operational measures and technologies, one column per energy demand type in port (electrical and heat). |
| Energy                                | GJ/year                     | The total energy demand at sea and in port after operational measures and technologies.      |
| TotalEnergyPort                       | GJ/year                     | The total energy demand in port across demand types.                                         |
| Saving                                | GJ/GJ                       | Relative reduction of the energy demand from operational measures and technologies, one column per energy demand type. |
| BaselineEnergy                        | GJ/year                     | The year-0 raw energy intensity applied to the transport work actually performed.            |
| ConsumedEnergy                        | GJ/year                     | Fuel consumed in energy for all fuels.                                                       |
| FuelTypeEnergy                        | GJ/year                     | Fuel consumed in energy, aggregated by fuel type.                                            |
| TotalConsumedEnergy                   | GJ/year                     | Total consumed energy across all fuels plus shore power.                                     |
| ShorePowerEnergy                      | GJ/year                     | Shore power energy supplied.                                                                 |
| ConverterEnergy                       | GJ/year                     | Fuel consumed in energy in vessels of a fuel type across fuels per fuel type.                |
| PilotFuelShare                        | Ton/ton                     | The fraction of total fuel spent which is pilot fuel for each vessel fuel type.              |
| EquivalentWtt                         | Ton CO<sub>2</sub>-eq./year | Emitted well-to-tank emissions per fuel and emission.                                        |
| TotalEquivalentWtt                    | Ton CO<sub>2</sub>-eq./year | Total emitted well-to-tank emissions.                                                        |
| EquivalentTtw                         | Ton CO<sub>2</sub>-eq./year | Emitted Tank-to-wake emissions per fuel and emission.                                        |
| TotalEquivalentTtw                    | Ton CO<sub>2</sub>-eq./year | Total emitted tank-to-wake emissions.                                                        |
| EquivalentWtw                         | Ton CO<sub>2</sub>-eq./year | Emitted well-to-wake emissions per fuel and emission.                                        |
| TotalEquivalentWtw                    | Ton CO<sub>2</sub>-eq./year | Total emitted well-to-wake emissions across all fuels plus shore power.                      |
| ShorePowerEmission                    | Ton/year                    | Shore power emission per emission (well-to-wake lump, no WTT/TTW split).                     |
| CumulativeEquivalentWtt               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted well-to-tank emissions per fuel and emission.                             |
| CumulativeTotalEquivalentWtt          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted well-to-tank emissions.                                             |
| CumulativeEquivalentTtw               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted tank-to-wake emissions per fuel and emission.                             |
| CumulativeTotalEquivalentTtw          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted tank-to-wake emissions.                                             |
| CumulativeEquivalentWtw               | Ton CO<sub>2</sub>-eq.      | Cumulative emitted well-to-wake emissions per fuel and emission.                             |
| CumulativeTotalEquivalentWtw          | Ton CO<sub>2</sub>-eq.      | Cumulative total emitted well-to-wake emissions, including shore power.                      |
| IntensityEquivalentWtt                | Kg CO<sub>2</sub>-eq./GJ    | Emitted well-to-tank emissions per fuel and emission, per total consumed energy (including shore power). |
| IntensityTotalEquivalentWtt           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted well-to-tank emissions per total consumed energy (including shore power).      |
| IntensityEquivalentTtw                | Kg CO<sub>2</sub>-eq./GJ    | Emitted tank-to-wake emissions per fuel and emission, per total consumed energy (including shore power). |
| IntensityTotalEquivalentTtw           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted tank-to-wake emissions per total consumed energy (including shore power).      |
| IntensityEquivalentWtw                | Kg CO<sub>2</sub>-eq./GJ    | Emitted well-to-wake emissions per fuel and emission, per total consumed energy (including shore power). |
| IntensityTotalEquivalentWtw           | Kg CO<sub>2</sub>-eq./GJ    | Total emitted well-to-wake emissions across all fuels plus shore power, per total consumed energy (including shore power). |
| LevyUnits                             | Ton                         | Emission units charged by a levy, one column per levy.                                       |
| RemedialUnits                         | Ton                         | Remedial compliance units required, one column per regulation.                               |
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
| SpeedEnergyIntensitySaving            | GJ/GJ    | Relative reduction of energy intensity from speed changes, against the year-0 raw intensity performing the actual transport work. |
| OperationalEnergyIntensitySaving      | GJ/GJ    | Relative reduction of energy intensity from speed and operational measures, against the year-0 raw intensity performing the actual transport work. |
| TechnologyEnergyIntensitySaving       | GJ/GJ    | Relative reduction of energy from added technologies.                  |
| EnergyIntensitySaving                 | GJ/GJ    | Relative reduction of energy intensity from speed, operational measures, and technologies, against the year-0 raw intensity performing the actual transport work. |
| InstalledPower                        | MW       | Installed power per fuel type.                                         |
| NewbuildPower                         | MW/year  | Installed power for newbuilds per fuel type.                           |
| ScrappedPower                         | MW/year  | Installed power scrapped per fuel type.                                |
| FuelConvertedPower                    | MW/year  | Installed power fuel converted per fuel type to fuel type.             |
| CumulativeNewbuildPower               | MW       | Cumulative installed power for newbuilds per fuel type.                |
| CumulativeScrappedPower               | MW      | Cumulative installed power scrapped per fuel type.                     |
| CumulativeFuelConvertedPower          | MW       | Cumulative installed power fuel converted per fuel type to fuel type.  |
| WeightedAverageAge                    | Year     | Power-weighted average age of the vessels in the fleet per fuel type.  |
| VesselExpenses                        | USD/year | Running expenses of acquisition of all vessels.                        |
| TechnologyExpenses                    | USD/year | Running levelized expenses of all installed technologies.              |
| FuelConversionExpenses                | USD/year | Running expenses of all fuel conversions.                              |
| VesselRelatedExpenses                 | USD/year | Running expenses of all vessels.                                       |
| Expenses                              | USD/year | Running expenses including fuel of all vessels.                        |
| CumulativeVesselExpenses              | USD      | Cumulative running expenses of acquisition of all vessels.             |
| CumulativeTechnologyExpenses          | USD      | Cumulative running levelized expenses of all installed technologies.   |
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
| FleetEvolutionTime   | Second | The time spent calculating the evolution of the fleet nodes.                       |
| ProducerEvolutionTime | Second | The time spent calculating the evolution of the producer nodes.                    |
| ExistingBuildTime    | Second | The LP build time for the existing bunker decision.                                |
| ExistingSolveTime    | Second | The LP solve time for the existing bunker decision.                                |
| ExistingTransferTime | Second | The transfer time for the results of the existing bunker decision.                 |
| TemporalTime         | Second | The time spent assigning the temporal calculators and precalculating expectations. |
| VesselTime           | Second | The time spent on the operational profiles and charter properties of the vessels.  |
| FuelSupplyTime       | Second | The time spent on the production, logistics and port import properties of the fuels. |
| PolicyTime           | Second | The time spent on the policy emission coefficients and the fair share fuel supply. |
| FleetStateTime       | Second | The time spent updating increment ages, fleet evolution expectations and the missing technology approximation. |
| ProfileAggTime       | Second | The time spent aggregating the profiles of the fleet, port, producer, regulation and vessel nodes. |
| OverheadTime         | Second | The time spent initializing the existing fleet and production, and updating the investment signal beliefs. |

The properties are applicable for the following commands:

* `add_fleet_property`

| **Property name**                  | **Unit**          | **Description**                                                                                 |
|------------------------------------|-------------------|-------------------------------------------------------------------------------------------------|
| Trade                              | Cargo-miles/year  | Trade satisfied.                                                                                |
| CargoMiles                         | Cargo-miles/year  | Transport work performed.                                                                       |
| ExistingVessels                    | # of vessels      | Number of existing vessels per vessel.                                                          |
| Scrap                              | # of vessels/year | Number of vessels scrapped (primary and secondary) per vessel.                                  |
| Newbuilds                          | # of vessels/year | Number of newbuild vessels per vessel.                                                          |
| FuelConversions                    | # of vessels/year | Number of vessels fuel converted per vessel to vessel.                                          |
| TechnologyUptake                   | Fraction of fleet | Fraction of vessels with the technology installed per vessel and technology.                    |
| FleetTechnologyUptake              | Fraction of fleet | Fraction of vessels with the technology installed, weighted by the existing vessel count, per technology. |
| NewbuildTechnologyUptake           | Fraction of fleet | Fraction of newbuild vessels with the technology installed per vessel and technology.           |
| RetrofitTechnologyUptake           | Fraction of fleet | Fraction of vessels retrofitted with the technology per vessel and technology.                  |
| ReferenceSpeed                     | Knots             | The average reference (speed defined in Route) speed across all vessels.                        |
| MinimumSpeed                       | Knots             | The average minimum speed attainable across all vessels.                                        |
| MaximumSpeed                       | Knots             | The average maximum speed attainable across all vessels.                                        |
| ActualSpeed                        | Knots             | The average speed across all vessels.                                                           |
| OptimalSpeed                       | Knots             | The average optimal speed across all vessels.                                                   |
| LowestSpeed                        | Knots             | The lowest actual speed across all vessels.                                                     |
| HighestSpeed                       | Knots             | The highest actual speed across all vessels.                                                    |
| InstantaneousFreightRate           | USD/cargo-nautical mile | Charter cost of the fleet per cargo-mile delivered, includes fuel and technology expenses.      |


The properties are applicable for the following commands:

* `add_producer_property`

| **Property name**               | **Unit**         | **Description**                                                                  |
|---------------------------------|------------------|----------------------------------------------------------------------------------|
| MaximumDevelopment              | # of plants/year | Number of plants that can be added to the pipeline across all plants.            |
| Development                     | # of plants/year | Number of plants added to the pipeline across all plants.                        |
| CumulativeMaximumDevelopment    | # of plants      | Cumulative number of plants that can be added to the pipeline across all plants. |
| CumulativeDevelopment           | # of plants      | Cumulative number of plants added to the pipeline across all plants.             |
| FairShareFuelFraction           | Fraction         | Fraction of fuel demand allocated to the producer to supply.                     |

The properties are applicable for the following commands:

* `add_vessel_property`

| **Property name**       | **Unit**                  | **Description**                                                           |
|-------------------------|---------------------------|---------------------------------------------------------------------------|
| Lifetime                | Year                      | Lifetime of the vessel.                                                   |
| LeadTime                | Year                      | Lead time of the vessel, used only in its levelized cost.                 |
| CargoMiles              | Cargo-miles/year          | Transport work performed.                                                 |
| ReferenceSpeed          | Knots                     | Average reference speed (speed defined in Route) of the vessel.           |
| MinimumSpeed            | Knots                     | Average minimum speed attainable.                                         |
| MaximumSpeed            | Knots                     | Average maximum speed attainable.                                         |
| ActualSpeed             | Knots                     | Average actual speed.                                                     |
| OptimalSpeed            | Knots                     | Average optimal speed.                                                    |
| LowestSpeed             | Knots                     | Lowest actual speed.                                                      |
| HighestSpeed            | Knots                     | Highest actual speed.                                                     |
| SpeedEnergySaving       | GJ/GJ                     | Relative reduction of all energy demand due to speed changes.             |
| OperationalEnergySaving | GJ/GJ                     | Relative reduction of all energy demand due to operational changes.       |
| TechnologyEnergySaving  | GJ/GJ                     | Relative reduction of all energy demand from added technologies.          |
| EnergySaving            | GJ/GJ                     | Relative reduction of all energy from operational and technology changes. |
| SpeedEnergyIntensitySaving | GJ/GJ                  | Relative reduction of energy per cargo-mile from speed changes.           |
| OperationalEnergyIntensitySaving | GJ/GJ            | Relative reduction of energy per cargo-mile from speed and operational changes. |
| TechnologyEnergyIntensitySaving | GJ/GJ             | Relative reduction of energy from added technologies.                     |
| EnergyIntensitySaving   | GJ/GJ                     | Relative reduction of energy per cargo-mile from speed, operational, and technology changes. |
| AssetCharterRate        | USD/year                  | Asset charter rate (owner to operator), does not include fuel or technology expenses. |
| CargoCharterRate        | USD/year                  | Cargo charter rate (operator to cargo owner), includes fuel and technology expenses. |
| TechnologyCost          | USD/year                  | Fleet-average levelized cost of installed technologies.                   |
| InvestmentFreightRate   | USD/cargo-nautical mile   | Long-run freight rate at the time of investment, includes fuel and technology expenses. |
| InstantaneousFreightRate | USD/cargo-nautical mile  | Long-run freight rate at the actual conditions of the vessel, includes fuel and technology expenses. |
| InvestmentSignalTechnology | USD/GJ                    | Energy-weighted average of the smoothed energy conservation duals over the technology horizon. |
| InvestmentSignalSpeed   | USD/GJ                    | Energy-weighted average of the smoothed energy conservation duals over the speed horizon. |


The properties are applicable for the following commands:

* `add_plant_property`

| **Property name**                        | **Unit**                    | **Description**                                                                 |
|------------------------------------------|-----------------------------|---------------------------------------------------------------------------------|
| InvestmentCost                           | USD/ton                     | Levelized production cost at time of investment.                                |
| InvestmentIntensityCost                  | USD/GJ                      | Levelized production cost at time of investment per energy in fuel.             |
| InstantaneousCost                        | USD/ton                     | Supply-weighted average cost over all plants.                                   |
| InstantaneousIntensityCost               | USD/GJ                      | Supply-weighted average cost over all plants per energy in fuel.                |
| EquivalentInvestmentWtt                  | Ton CO<sub>2</sub>-eq./ton  | Well-to-tank emissions at time of investment per ton of fuel per emission.      |
| TotalEquivalentInvestmentWtt             | Ton CO<sub>2</sub>-eq./ton  | Total well-to-tank emissions at time of investment per ton of fuel.             |
| IntensityEquivalentInvestmentWtt         | Ton CO<sub>2</sub>-eq./GJ   | Well-to-tank emissions at time of investment per energy in fuel per emission.   |
| IntensityTotalEquivalentInvestmentWtt    | Ton CO<sub>2</sub>-eq./GJ   | Total well-to-tank emissions at time of investment per energy in fuel.          |
| EquivalentInstantaneousWtt               | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average well-to-tank emissions per ton of fuel per emission.    |
| TotalEquivalentInstantaneousWtt          | Ton CO<sub>2</sub>-eq./ton  | Supply-weighted average total well-to-tank emissions per ton of fuel.           |
| IntensityEquivalentInstantaneousWtt      | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average well-to-tank emissions per energy in fuel per emission. |
| IntensityTotalEquivalentInstantaneousWtt | Ton CO<sub>2</sub>-eq./GJ   | Supply-weighted average total well-to-tank emissions per energy in fuel.        |

The properties are applicable for the following commands:

* `add_port_property`

| **Property name**                 | **Unit**                   | **Description**                                                                 |
|-----------------------------------|----------------------------|---------------------------------------------------------------------------------|
| BunkeringAllowed                  | Boolean                    | Whether bunkering is allowed at the port, per fuel.                             |
| BunkerPrice                       | USD/ton                    | Bunker price per ton of fuel.                                                   |
| BunkerIntensityPrice              | USD/GJ                     | Bunker price per energy in fuel.                                                |
| BunkerWtt                         | Ton/ton                    | Well-to-tank emissions of bunker fuel per ton of fuel per fuel and emission.    |
| EquivalentBunkerWtt               | Ton CO<sub>2</sub>-eq./ton | Well-to-tank emissions of bunker fuel per ton of fuel per fuel and emission.    |
| TotalEquivalentBunkerWtt          | Ton CO<sub>2</sub>-eq./ton | Well-to-tank emissions of bunker fuel per ton of fuel per fuel.                 |
| BunkerIntensityWtt                | Ton/GJ                     | Well-to-tank emissions of bunker fuel per energy in fuel per fuel and emission. |
| BunkerIntensityEquivalentWtt      | Ton CO<sub>2</sub>-eq./GJ  | Well-to-tank emissions of bunker fuel per energy in fuel per fuel and emission. |
| BunkerIntensityTotalEquivalentWtt | Ton CO<sub>2</sub>-eq./GJ  | Well-to-tank emissions of bunker fuel per energy in per fuel.                   |

The properties are applicable for the following commands:

* `add_regulation_property`

| **Property name**   | **Unit** | **Description**                                        |
|---------------------|----------|--------------------------------------------------------|
| FlexibilityCost     | USD/ton  | Cost of flexibility compliance unit.                   |
| RemedialCost        | USD/ton  | Cost of remedial compliance unit.                      |
| VesselThreshold     | Unit\*   | Allowable emissions measure per vessel.                |
| AdjustedVesselThreshold | Unit\*   | Allowable emissions measure per vessel after threshold adjustment of an INDIVIDUAL regulation. |
| SharedThreshold     | Unit\*   | Fleet-level effective target of a FLEXIBLE regulation. |
| AdjustedSharedThreshold | Unit\*   | Fleet-level effective target of a FLEXIBLE regulation after threshold adjustment. |
| VesselCompliance    | Unit\*   | Achieved emissions measure per vessel.                 |
| SharedCompliance    | Unit\*   | Total achieved emissions measure.                      |
| VesselAllowance     | Ton      | Allowed emissions per vessel.                          |
| SharedAllowance     | Ton      | Total allowed emissions across the policed vessels.    |
| VesselUnits         | Ton      | Achieved emissions per vessel.                         |
| SharedUnits         | Ton      | Total achieved emissions across the policed vessels.   |
| NonComplianceUnits  | Ton      | Flexibility and remedial compliance units combined.    |
| SurplusUnits        | Ton      | Surplus compliance units generated.                    |
| FlexibilityUnits    | Ton      | Flexibility compliance units used.                     |
| RemedialUnits       | Ton      | Remedial compliance units required.                    |
| SurplusRevenue      | USD/ton  | Revenue from selling surplus compliance units.         |
| FlexibilityExpenses | USD/ton  | Expenses from purchasing flexibility compliance units. |
| RemedialExpenses    | USD/ton  | Expenses from purchasing remedial compliance units.    |

\*Depends on the ‘Measure’ of the regulation (ABSOLUTE=ton, INTENSITY=kg/GJ, TRANSPORT\_NOMINAL=g/nominal cargo-nautical mile, TRANSPORT=g/actual cargo-nautical mile)

The properties are applicable for the following commands:

* `add_levy_property`

| **Property name** | **Unit**  | **Description**                                                        |
|-------------------|-----------|------------------------------------------------------------------------|
| Collected         | USD/year  | Revenue collected or paid out via penalties or subsidies respectively. |
