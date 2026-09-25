<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Fleet

A `Fleet` node defines a segment of vessels and is used to control the decisions made by actors of that segment.
Examples of fleets are handymax bulk carriers and LR1 tankers.

Example:

```python
Fleet "tug" {
    Vessels = [Vessel("tug_ice_oil"),
               Vessel("tug_ice_ammonia"),
               Vessel("tug_ice_methane"),
               Vessel("tug_ice_methanol")]

    InitialVessels = 8464

    InitialSplit = [0.998,
                    0.000,
                    0.002,
                    0.000]

    Orderbooks = [Forecast("tug_orderbook_oil"),
                  Forecast("tug_orderbook_ammonia"),
                  Forecast("tug_orderbook_methane"),
                  Forecast("tug_orderbook_methanol")]

    TradeGrowth = Forecast("tug_trade_growth")
}
```


## Attributes

### Vessels 

This attribute sets the list of vessel types that exist for the fleet. Vessel types can be viewed as a discretization of the fuel types and technologies of the fleet.

* **Data type**: List of `Vessel` nodes
* **Example values**:
  + `[Vessel("name1"), Vessel("name2")]`
  + `[Vessel("*")]`
* **Default**: None. Must be provided by the user.

### Inertia

This attribute defines the inertia used in the uptake decision of newbuild vessels. The inertia is defined as the fraction of newbuilds that must follow the same vessel type distribution as the previous time-step.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.66`
  + `Forecast("name")`
* **Unit**: Fraction/year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### Memory

This attribute sets the exponential decay of the memory of the fleet used in the expected uptake decision of newbuild vessels. A high memory means that the expected uptake of newbuild vessels is more stable.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.66`
  + `Forecast("name")`
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0.5

### FixedScrapRate

This attribute sets the fixed scrap rate of the fleet in fraction/year. If the fixed scrap rate is set it overwrites the age-based scrapping functionality resulting in vessels potentially being scrapped prior to their technical lifetime.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.1`
  + `Forecast("name")`
* **Unit**: Fraction/year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: None.

### AllowSecondaryScrapping

This attribute sets whether secondary scrapping is permitted. Secondary scrapping occurs if a drop in trade is not offset by the amount of scrapped vessels. If secondary scrapping is not allowed the actual capacity of the fleet may be higher than the projected trade.

* **Data type**: `Boolean`
* **Default**: TRUE

### InterFuelSensitivity

Set how strongly newbuild fuel-type choice responds to the levelized cost of transport (LCOT).

The value is an odds ratio against a 10% increase: a fuel whose LCOT is 10% higher receives this many times the odds of an otherwise identical fuel. For example `0.5` means a 10%-higher LCOT halves the odds, and `1` means no preference. LCOT is lower-is-better, so use a value below `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `0.5`
* **Minimum value**: 0 (exclusive)
* **Default**: None. Must be provided by the user.

### IntraFuelSensitivity

Set how strongly newbuild technology-variant choice within a single fuel type responds to the levelized cost of transport (LCOT).

The value is an odds ratio against a 10% increase: a variant whose LCOT is 10% higher receives this many times the odds of an otherwise identical variant. For example `0.5` means a 10%-higher LCOT halves the odds, and `1` means no preference. Use a value below `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `0.5`
* **Minimum value**: 0 (exclusive)
* **Default**: None. Must be provided by the user.

### TechnologySensitivity

Set how strongly the energy-saving technology-package choice responds to its net present value (NPV).

The value is an odds ratio against an advantage equal to 5% of the summed ship CAPEX: a package whose NPV advantage equals 5% of the ship CAPEX receives this many times the odds of an otherwise identical package. For example `2` means such an advantage doubles the odds, and `1` means no preference. NPV is higher-is-better, so use a value above `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `2`
* **Minimum value**: 0 (exclusive)
* **Default**: None. Must be provided by the user when technologies are defined.

### TechnologyCostOfCapital

This attribute sets the cost of capital used for evaluating technology investments. It represents the discount rate used to evaluate the net present value of technology investments and retrofits.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.08`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Default**: None

### TechnologyHorizon

Smoothing horizon (in years) for the energy-scarcity belief that scales technology marginal-saving evaluations. A longer horizon dampens transient LP shadow-price spikes, so newbuild technology choices respond to persistent scarcity rather than year-to-year noise.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `3`
  + `Forecast("name")`
* **Unit**: Years
* **Default**: 3

### SpeedHorizon

Smoothing horizon (in years) for the energy-scarcity belief that scales speed marginal-saving evaluations. Speed is an operational decision and typically uses a shorter horizon than `TechnologyHorizon` so it can respond faster to real tightness.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1`
  + `Forecast("name")`
* **Unit**: Years
* **Default**: 1

### TradeGrowth

This attribute sets the trade-growth rate of the fleet, expressed in fraction/year.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.05`
  + `Forecast("name")`
* **Unit**: Fraction/year
* **Default**: 0

### InitialVessels 

This attribute sets the initial number of vessels in the fleet.

A minimum of one vessel is necessary to compound the trade-growth.

* **Data type**: `Float`
* **Example values**: `150`
* **Unit**: Number of vessels
* **Minimum value**: 1
* **Default**: None. Must be defined by the user.

### InitialSplit

This attribute sets the initial distribution of vessel types in the fleet.

The list must have the same length as the list of vessels.

The list must sum to 1. If not, the list is normalized by equal fractions.

* **Data type**: List of `floats`
* **Example values**:
  + `[0.3, 0.7]`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: Determined through internal calculations.

### InitialAgeDistribution

This attribute sets the initial age distribution of each vessel type in the fleet.

The list must have a length corresponding to the number of vessel types. Each entry is either a Curve reference (where the Curve's x-values are ages in increasing order and y-values are the corresponding fractions) or `0` for vessel types with no custom distribution.

* **Data type**: List of `Curve` nodes and/or `0`
* **Example values**:
  + `[Curve("age_dist_1"), 0, Curve("age_dist_3")]`
* **Minimum value**: 0
* **Default**: None

### RetrofitFrequency

This attribute sets the retrofit frequency, namely the intervals at which a vessel can retrofit technology or perform a fuel conversion.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `5`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 5

### Orderbooks

This attribute sets the list of orderbooks used for determining the newbuild uptake from orderbooks, i.e. defines the number of new vessels of a certain vessel type in a given year.

The list must have the same length as the list of vessels.

If the orderbook is a forecast, it must be non-strictly increasing (meaning that it cannot decrease as time progresses in the forecast).

* **Data type**: List of `floats`, `Forecasts`, `Variables`
* **Example values**:
  + `[Forecast("name"), 0]`
* **Unit**: Number of vessels.
* **Minimum value**: 0
* **Default**: None

### AllowSpeedManagement

This attribute sets the flag for whether speed management is allowed.

Speed management dynamically optimizes the speed profile of each vessel type based on a cost optimal approach between adding newbuilds to the model versus the change in fuel expenses,

* **Data type**: `Boolean`
* **Default**: None

### MaximumSpeedChange

This attribute sets the maximum speed change permissible per year during dynamic speed management.

* **Data type**: `float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Minimum value**: 0
* **Default**: INF

### SpeedAlignment

This attribute sets the method used to align speed across vessel types within the fleet. Speed alignment determines how the individually optimized speeds are reconciled across vessel types.

* **Data type**: `ID`
* **Legal values**: [SpeedAlignmentID](appendix_ids.md#speedalignmentid)
* **Default**: INDIVIDUAL

### AssumeReferenceSpeedOptimal

This attribute sets the flag for whether the reference speed is assumed to be the current market optimum. When enabled, the route reference speed is treated as the market optimum (accounting for effects not modelled) and speed changes only occur relative to shifts in the modelled optimal speed.

* **Data type**: `Boolean`
* **Default**: FALSE

### FuelConversionSensitivity

Set how strongly the fuel-conversion choice responds to its net present value (NPV).

The value is an odds ratio against an advantage equal to 5% of the summed ship CAPEX: a conversion whose NPV advantage equals 5% of the ship CAPEX receives this many times the odds of an otherwise identical conversion (the do-nothing option has an NPV of zero). For example `2` means such an advantage doubles the odds, and `1` means no preference. NPV is higher-is-better, so use a value above `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `2`
* **Minimum value**: 0 (exclusive)
* **Default**: 2

### FuelConversionMinimumAge

This method sets the minimum age for fuel conversion in years.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `5`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 0

### Technologies

This attribute sets the list of technologies which can be installed on vessels in the fleet either directly on newbuilds or via retrofit to existing vessels.

Every Technology node assigned must be unique.

* **Data type**: List of `Technology` nodes
* **Example values**:
  + `[Technology("name1"), Technology("name2")]`
* **Default**: None

### AllowTechnologyApproximation

This attribute sets the flag for whether the fleet should approximate technology uptake based on the average impact of technology uptake on other fleets which model it bottom-up. If there is no fleet which models the technology bottom-up, then the technology uptake is set to zero.

* **Data type**: `Boolean`
* **Default**: TRUE

## Commands

### set\_initial\_technology\_share

This command sets the initial technology uptake as a function of vessel age. The Curve's x-axis is vessel age and its y-axis is the uptake fraction in `[0, 1]`. Wildcards are supported in both keys.

* **Primary key type**: String (Vessel name; supports wildcards)
* **Secondary key type**: String (Technology name; supports wildcards)
* **Data type**: `Curve` node
* **Example values**:
  + `"vessel_name", "technology_name", Curve("uptake_curve")`
  + `"*oil*", "hull_painting*", Curve("uptake_hull_painting")`
* **Unit**: x: Years, y: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: None

### set\_fuel\_conversion\_cost

This command sets the cost of performing a fuel conversion from one vessel type to another, in USD.

* **Primary key type**: String (Vessel name)
* **Secondary key type**: String (Vessel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name_from", "vessel_name_to", 10e6`
  + `"vessel_name_from", "vessel_name_to", Forecast("name")`
* **Unit**: USD
* **Minimum value**: 0
* **Default**: None

### set\_allow\_vessel

This command sets a boolean flag indicating whether a specific vessel from the list is allowed in the fleet.

If this command is set to FALSE, the vessel can neither enter the fleet as a newbuild nor enter the fleet through a fuel conversion.

Any existing vessels in the fleet however are unaffected.

This flag supersedes both attributes ‘Newbuild Available’ and 'Conversion Available'.

* **Primary key type**: String (Vessel name)
* **Data type**: `Boolean`
* **Example values**:
  + `"vessel_name", TRUE`
  + `"vessel_name", FALSE`
* **Default**: TRUE

### set\_newbuild\_available

This command sets a boolean flag indicating whether a specific vessel from the list is allowed as a newbuild in the fleet.

If this attribute is set to FALSE the vessel cannot enter the fleet as a newbuild.

* **Primary key type**: String (Vessel name)
* **Data type**: `Boolean`
* **Example values**:
  + `"vessel_name", TRUE`
  + `"vessel_name", FALSE`
* **Default**: TRUE

### set\_conversion\_available

This command sets a boolean flag indicating whether a specific vessel is allowed to undergo fuel conversion in the fleet.

If this command is set to FALSE it is not possible to perform fuel conversions to vessels of that type.

* **Primary key type**: String (Vessel name)
* **Data type**: `Boolean`
* **Example values**:
  + `"vessel_name", TRUE`
  + `"vessel_name", FALSE`
* **Default**: TRUE

### set\_newbuild\_limit

This command sets the maximum share of a single time-step's newbuild cargo-miles that can be delivered by a given vessel type. The limit is enforced across the orderbook, inertia, and modelled-uptake newbuild sources, so the cumulative share across the three sources cannot exceed the configured value.

* **Primary key type**: String (Vessel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name", 0.4`
  + `"*ammonia*", Forecast("name")`
* **Unit**: Fraction per year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### set\_fuel\_conversion\_limit

This command sets the cap on fuel conversions from one vessel type to another, as the fraction of the total fleet allowed to convert on that pair per year. For example, in a fleet of 100 vessels, a limit of 0.05 allows at most 5 vessels per year to convert from `vessel_name_from` to `vessel_name_to`.

* **Primary key type**: String (Vessel name being converted from; supports wildcards)
* **Secondary key type**: String (Vessel name being converted to; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name_from", "vessel_name_to", 0.05`
  + `"vessel_name_from", "vessel_name_to", Forecast("name")`
* **Unit**: Fraction per year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### set\_newbuild\_technology\_limit

This command sets the maximum fraction of the existing fleet that can install a given technology on newbuilds in one year. The cap is applied per technology and is independent of the retrofit cap set with `set_retrofit_technology_limit`.

* **Primary key type**: String (Technology name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"technology_name", 0.05`
  + `"technology_name", Forecast("name")`
* **Unit**: Fraction per year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### set\_retrofit\_technology\_limit

This command sets the maximum fraction of the existing fleet that can retrofit a given technology in one year. The cap is applied per technology and is independent of the newbuild cap set with `set_newbuild_technology_limit`.

* **Primary key type**: String (Technology name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"technology_name", 0.03`
  + `"technology_name", Forecast("name")`
* **Unit**: Fraction per year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### set\_operational\_saving\_sea

This command sets the fraction of energy saved at sea through operational measures that are not modeled through technology business cases. Examples include Just-In-Time (JIT) arrival, weather routing, trim optimization, and similar zero-cost energy reduction methods.

The operational saving is applied as an intermediate step between the raw energy demand (from speed/operation) and the technology-adjusted energy demand. It reduces the baseline energy against which technology savings are evaluated.

* **Primary key type**: [EnergyDemandTypeID](appendix_ids.md#energydemandtypeid)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `PROPULSION, 0.1`
  + `ELECTRICAL, Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### set\_operational\_saving\_port

This command sets the fraction of energy saved in port through operational measures that are not modeled through technology business cases.

The operational saving is applied as an intermediate step between the raw energy demand and the technology-adjusted energy demand.

* **Primary key type**: [EnergyDemandTypeID](appendix_ids.md#energydemandtypeid)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `ELECTRICAL, 0.05`
  + `HEAT, Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0
