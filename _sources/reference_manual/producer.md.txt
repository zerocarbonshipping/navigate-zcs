<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Producer

A `Producer` node defines an engineering, procurement, and construction (EPC) market for fuel production and is
used to control the decisions made by actors of that market.  Examples of producers are the global EPC market
for large scale methanol, ammonia, methane, and diesel plants and regional markets for bio-methane plants.

Example:

```python
Producer "engineering_procurement_construction" {
    Plants = [Plant("plant_methane_electro"), Plant("plant_ammonia_blue")]

    FuelDemandSensitivity = 1.25
    FuelCostSensitivity = 0.5
}
```

## Attributes

### Plants 

This attribute defines a list of plant types that can be built.

All 'Plants' must be unique, i.e., a plant cannot be duplicated in the input list

* **Data type**: List of `Plant` nodes
* **Example values**:
  + `[Plant("name1"), Plant("name2")]`
  + `[Plant("*")]`
* **Default**: None

### Inertia

This attribute sets the inertia used in the uptake decision of newbuild plants.

The inertia is defined as the fraction of newbuilds that must follow the same plant type distribution as the previous time-step. It is defined in fraction/year.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.66`
  + `Forecast("name")`
* **Unit**: fraction/year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### MinimumOfftakeDuration

This attribute sets the minimum offtake duration required for building new plants.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `7`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 1

### FuelDemandSensitivity

Set how strongly the split between plants producing different fuel pathways responds to expected demand.

The value is an odds ratio against a 10% increase: a pathway whose expected demand is 10% higher receives this many times the odds of an otherwise identical pathway. For example `1.25` means a 10%-higher demand gives 1.25 times the odds, and `1` means no preference. Demand is higher-is-better, so use a value above `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `1.25`
* **Minimum value**: 0 (exclusive)
* **Default**: None. Must be defined by the user

### FuelCostSensitivity

Set how strongly the split between plants producing the same fuel responds to the levelized cost of fuel (LCoF).

The value is an odds ratio against a 10% increase: a plant whose LCoF is 10% higher receives this many times the odds of an otherwise identical plant. For example `0.5` means a 10%-higher LCoF halves the odds, and `1` means no preference. LCoF is lower-is-better, so use a value below `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `0.5`
* **Minimum value**: 0 (exclusive)
* **Default**: None. Must be defined by the user

### InitialCapacity

This attribute sets the list of initial capacity for each plant type in tons/day.

The list must have the same length as the list of plants.

* **Data type**: List of `float`
* **Example values**:
  + `[500, 0]`
* **Default**: None

### InitialAgeDistribution

This attribute sets the initial age distribution of each plant type.

The list must have a length corresponding to the number of plant types. Each entry is either a Curve reference (where the Curve's x-values are ages in increasing order and y-values are the corresponding fractions) or `0` for plant types with no custom distribution.

* **Data type**: List of `Curve` nodes and/or `0`
* **Example values**:
  + `[Curve("age_dist_1"), 0, Curve("age_dist_3")]`
* **Minimum value**: 0
* **Default**: None

### MaximumDevelopment

This attribute sets the development constraint limiting the maximum number of plants which can be built per year.

While this attribute can be unassigned the simulation is better behaved if it is assigned. It can just be assigned arbitrarily high if an unconstrained scenario is required.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `10`
  + `Forecast("name")`
* **Unit**: Plants/year
* **Minimum value**: 0
* **Default**: None

### MaximumRampUp

This attribute sets the maximum ramp-up for the utilization of the development constraint per year.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.2`
  + `Forecast("name")`
* **Unit**: plants per year
* **Minimum value**: 0
* **Default**: 0

### JumpStartFraction

This attribute sets the jump-start fraction used to initiate the supply/demand interaction if there has been no production.

* **Data type**: `Float`
* **Example values**:
  + `0.1`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

## Commands

### set\_existing\_pipeline

This command sets an existing pipelines for a given plant used for determining the new plants from the pipeline.

The pipeline forecast must be non-strictly increasing.

* **Primary key type**: String (Plant name)
* **Data type**: `Forecast`
* **Example values**:
  + `"plant_name", Forecast("name")`
* **Unit**: tons/day/year
* **Minimum value**: 0
* **Default**: None

### set\_allow\_plant

This command sets a boolean flag for a given plant from the list of plants whether it is allowed or not.

* **Primary key type**: String (Plant name)
* **Data type**: `Boolean`
* **Example values**:
  + `"plant_name", TRUE`
  + `"plant_name", FALSE`
* **Default**: TRUE

### set\_feed\_constraint

This command sets a static constraint for the amount of feed (feedstock or process output) available to the producer in tons/year.

* **Primary key type**: String (Feedstock name, Process name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
* "feedstock\_name", 1e6
  + "feedstock\_name, Forecast("name")
* **Unit**: tons / year
* **Minimum value**: 0
* **Default**: INF
