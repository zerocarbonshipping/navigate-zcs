<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Appendix - ID Overview

A range of IDs are included in Navigate. These are referred to in the node descriptions above. Below, all of them are explained and all possible IDs are listed.

## EnergyDemandTypeID

This ID describes the type of energy demand that is targeted by a certain technology.

| ID | Description |
| --- | --- |
| PROPULSION | The technology targets the energy demand for propelling the vessel forward.  Example: Kite, Flettner rotor. |
| ELECTRICAL | The technology targets the vessel’s electricity demand.  Example: Waste heat recovery system, lighting system. |
| HEAT | The technology targets the vessel’s heat demand.  Example: Exhaust gas boiler. |

## ExtrapolateID

The Extrapolate ID describes the method used for extrapolating in Curves and Forecasts.

| ID | Description |
| --- | --- |
| FALSE | Do not allow extrapolation. Error is thrown if attempting. |
| FLAT | Extrapolate flat from the closest value in the table. |
| LINEAR | Linear extrapolation from the last two values in the table. |

## FileFormatID

The FileFormat ID describes the file format used when exporting report data.

| ID | Description |
| --- | --- |
| XLSX | Export the report as a single Excel workbook with one sheet per report table. |
| CSV | Export the report as CSV files with one file per report table. |

## FuelTypeID

The fuel type describes the type of molecule that a fuel is based on. I.e., ‘fuel type’ is not synonymous with ‘fuel’.

Different fuels can have the same fuel type, as a fuel corresponds to a fuel-pathway (where the pathway describes how it was produced).

| ID          | Description                                                                                                          |
|-------------|----------------------------------------------------------------------------------------------------------------------|
| AMMONIA     | The fuel primarily consists of the molecule ammonia.  Fuel examples: Blue ammonia, e-ammonia, grey ammonia.          |
| ELECTRICITY | Not actually a fuel, but a way to implement battery-electric vessels.                                                |
| ETHANOL     | The fuel primarily consists of the molecule ethanol.  Fuel example: Bio-ethanol.                                     |
| HYDROGEN    | The fuel primarily consists of the molecule hydrogen.  Fuel examples: Blue hydrogen, e-hydrogen, grey hydrogen.      |
| LPG         | The fuel is a pressurized liquefied gas. Fuel examples: Butane and propane.                                          |
| METHANE     | The fuel primarily consists of the molecule methane.  Fuel examples: LNG, bio-methane.                               |
| METHANOL    | The fuel primarily consists of the molecule methanol.  Fuel examples: Bio-methanol, e-methanol.                      |
| OIL         | The fuel is an oil or diesel based fuel. Fuel examples: HFO, LFO, VLSFO, MDO, MGO, bio-diesel, bio-oil, or e-diesel. |

## Interpolate1DID

The Interpolate1D ID describes the method used for interpolating in Curves and Forecasts.

| ID | Description |
| --- | --- |
| LINEAR | Perform linear interpolation between points in the table. |
| PREVIOUS | Pick the previous value when interpolating. |
| NEXT | Pick the next value when interpolating |
| NEAREST | Pick the closest value when interpolating (rounding down at 0.5) |
| NEAREST\_UP | Pick the closest value when interpolating (round up at 0.5) |

## Interpolate2DID

The Interpolate2D ID describes the method used for interpolating in Surfaces and Timetables.

| ID | Description |
| --- | --- |
| LINEAR | Perform linear interpolation between points in the table. |
| NEAREST | Pick the closest value when interpolating (rounding down at 0.5) |

## LevySchemeID

These IDs describe the way that a levy will regulate emissions.

| ID | Description |
| --- | --- |
| PENALTY | The levy penalizes emissions |
| SUBSIDY | The levy subsidizes avoiding emissions and reaching below a set threshold |
| BOTH | The levy penalizes emissions above a set threshold and subsidizes avoiding emissions and reaching below the set threshold |

## PolicyScopeID

These IDs describe what emissions are included under the scope of the policy, in reference to what processes the emissions are due to.

| ID | Description |
| --- | --- |
| WTT | Short for: Well-to-tank  The emissions targeted under the policy are the ones associated with extracting resources and processing them into a bunker fuel. |
| TTW | Short for: Tank-to-wake  The emissions targeted under the policy are the ones associated with consuming the bunker fuel on a vessel. |
| WTW | Short for: Well-to-wake  The emissions targeted under the policy are the ones associated with extracting resources and processing them into a bunker fuel, as well as the ones associated with consuming the bunker fuel on a vessel. |

## RegulationMeasureID

These IDs describe the way that a regulation will measure emissions in terms of the scope of the measure.

| ID | Description |
| --- | --- |
| ABSOLUTE | Absolute emissions measured in mass of emissions (ton of emissions) |
| INTENSITY | Emissions intensity meaning emissions per energy consumed (ton of emissions per gigajoule, ton/GJ) |
| TRANSPORT\_NOMINAL | Emissions intensity per NOMINAL transport work (ton of emission per nominal cargo-mile) |
| TRANSPORT | Emissions intensity per ACTUAL transport work (ton of emission per actual cargo-mile) |

## RegulationSchemeID

These IDs describe the way that a regulation will regulate emissions.

| ID | Description |
| --- | --- |
| INDIVIDUAL | Every vessel must be compliant with the regulation and trading emission certificates from overcompliance is not possible. |
| FLEXIBLE | Vessels may trade emission certificates between them by certain vessels being overcompliant with the regulation. |

## ReportReduceID

ReportReduceID is used for reducing tuples in the reports for easier data manipulation.

| ID | Description |
| --- | --- |
| NONE | This means no reduction of the tuple(s) |
| FIRST | This means reduction over the first element of the tuple(s) |
| SECOND | This means reduction over the second element of the tuple(s) |
| BOTH | This means reduction over both elements of the tuple(s) |

## RouteTypeID

These IDs describe the principle of how the vessel moves between ports.

| ID | Description |
| --- | --- |
| ROUND\_TRIP | The defined start port is automatically considered the end port. The order in which the ports are entered determines the order in which the vessel visits them.  Individual legs of the journey are specified, allowing inputs for different distance, speeds and capacity utilization etc. on separate legs.  The same port can be visited more than once. |
| REGIONAL\_TRIP | There is no defined start or end port.  Individual legs of the journey are not specified. Instead, a distribution of fraction of time spent at different speeds and cargo capacity can be defined.  The same port can be visited more than once. |

## SolverBackendID

These IDs select the solver backend used to solve the bunker algorithm's linear program. HiGHS is installed with Navigate and always available; Gurobi requires the optional extra (`pip install .[gurobi]`) and a full Gurobi license.

| ID | Description |
| --- | --- |
| AUTOMATIC | Tries Gurobi first. If Gurobi is not installed or licensed, falls back to HiGHS. |
| GUROBI | Prefers Gurobi. If Gurobi is not available, falls back to HiGHS. |
| HIGHS | Skips Gurobi entirely and uses HiGHS directly. |

## SolverMethodID

These IDs select the LP solution method used by the solver backend. The values mirror Gurobi's `Method` parameter; the HiGHS backend uses its hybrid interior-point method regardless of this setting.

| ID | Description |
| --- | --- |
| AUTOMATIC | Let the solver choose the algorithm automatically. |
| DETERMINISTIC | Deterministic concurrent solve; results are reproducible from run to run. |
| NON\_DETERMINISTIC | Non-deterministic concurrent solve; may be faster but can vary from run to run. |

## SpeedAlignmentID

This ID describes how the individually optimized speeds are aligned across vessel types in a fleet during speed management.

| ID | Description |
| --- | --- |
| INDIVIDUAL | Each vessel type keeps its own optimal speed. |
| MINIMUM | All vessel types use the minimum optimal speed across the fleet. |
| MAXIMUM | All vessel types use the maximum optimal speed across the fleet. |
| AVERAGE | All vessel types use the weighted arithmetic mean of the optimal speeds. |

## SourceDependencyID

These IDs describe the type of dependency the electricity source has to the region

| ID | Description |
| --- | --- |
| STANDALONE | The electricity source for the production of fuels are standalone and not connected to the electricity grid in the region. |
| CONNECTED | The fuel production is connected to the region’s electricity grid. And the average emissions associated with electricity consumption in the defined region. |
