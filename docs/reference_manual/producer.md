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

All 'Plants' must be unique, i.e., a plant cannot be duplicated in the input list.

* **Data type**: List of `Plant` nodes
* **Example values**:
  + `[Plant("name1"), Plant("name2")]`
  + `[Plant("*")]`
* **Default**: None. Must be provided by the user.

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

This attribute sets the minimum offtake duration required for building new plants. The duration is rounded up to whole years, so a duration under one year counts as one year.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `7`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: >0
* **Default**: 1

### FuelDemandSensitivity

Set how strongly the split between plants producing different fuel pathways responds to expected demand.

The value is an odds ratio against a 10% increase: a pathway whose expected demand is 10% higher receives this many times the odds of an otherwise identical pathway. For example `1.25` means a 10%-higher demand gives 1.25 times the odds, and `1` means no preference. Demand is higher-is-better, so use a value above `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1.25`
  + `Forecast("name")`
* **Minimum value**: >0
* **Default**: None. Must be provided by the user.

### FuelCostSensitivity

Set how strongly the split between plants producing the same fuel responds to the levelized cost of fuel (LCoF).

The value is an odds ratio against a 10% increase: a plant whose LCoF is 10% higher receives this many times the odds of an otherwise identical plant. For example `0.5` means a 10%-higher LCoF halves the odds, and `1` means no preference. LCoF is lower-is-better, so use a value below `1`.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Minimum value**: >0
* **Default**: None. Must be provided by the user.

### InitialCapacity

This attribute sets the list of initial capacity for each plant type in tons/day.

The list must have the same length as the list of plants.

* **Data type**: List of `Float` and/or `Variable` nodes
* **Example value**: `[500, 0]`
* **Unit**: tons/day
* **Minimum value**: 0
* **Default**: 0 for every plant

### InitialAgeDistribution

This attribute sets the initial age distribution of each plant type.

The list must have a length corresponding to the number of plant types. Each entry is either a Curve reference (where the Curve's x-values are ages in increasing order and y-values are the corresponding fractions) or a number for plant types with no custom distribution. `0`, any other number, or leaving the attribute unset all give a uniform age spread over the plant's lifetime. The Curve's values must be finite.

* **Data type**: List of `Float` and/or `Curve` nodes
* **Example value**: `[Curve("age_dist_1"), 0, Curve("age_dist_3")]`
* **Minimum value**: 0
* **Default**: Not set. Every plant type gets a uniform age spread over its lifetime.

### MaximumDevelopment

This attribute sets the development constraint limiting the maximum number of plants which can be built per year.

If an unconstrained scenario is required, assign a value far above any development the demand could call for, such as `1e6`; `INF` is rejected.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `10`
  + `Forecast("name")`
* **Unit**: Plants/year
* **Minimum value**: 0
* **Default**: None. Must be provided by the user.

### MaximumRampUp

This attribute sets the maximum ramp-up for the utilization of the development constraint per year. The utilization is the fraction of `MaximumDevelopment` that can be used, and it cannot exceed 1.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.2`
  + `Forecast("name")`
* **Unit**: fraction/year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### JumpStartFraction

This attribute sets the jump-start fraction used to initiate the supply/demand interaction if there has been no production.

The expected uptake of the producer's plants blends the current uptake with an even split over the allowed plants, the even split weighted by the jump-start fraction. This blend applies in every time-step, so the fraction shapes the expectation also after production has started. While the development constraint has not been utilized, the jump-start fraction also stands in for its utilization.

* **Data type**: `Float`, `Variable`
* **Example values**:
  + `0.1`
  + `Variable("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0.1

## Commands

### set\_existing\_pipeline

This command sets an existing pipeline for a given plant, used for determining the new plants from the pipeline. The forecast gives the cumulative capacity committed up to each delivery date.

The pipeline forecast must be finite and non-strictly increasing. This command is only allowed in the `DEFINE` section.

* **Primary key type**: String (Plant name; supports wildcards)
* **Data type**: `Forecast`
* **Example value**: `"plant_name", Forecast("name")`
* **Unit**: tons/day
* **Minimum value**: 0
* **Default**: Not set. The plant has no committed pipeline.

### set\_allow\_plant

This command sets a boolean flag for a given plant from the list of plants whether it is allowed or not.

* **Primary key type**: String (Plant name; supports wildcards)
* **Data type**: `Boolean`
* **Example values**:
  + `"plant_name", TRUE`
  + `"plant_name", FALSE`
* **Default**: TRUE

### set\_feed\_constraint

This command sets a static constraint for the amount of feed (feedstock or process output) available to the producer in tons/year. `INF` means no constraint.

* **Primary key type**: String (Feedstock or Process name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"feedstock_name", 1e6`
  + `"feedstock_name", Forecast("name")`
* **Unit**: tons / year
* **Minimum value**: 0
* **Default**: Not set. The feed is unconstrained, as with `INF`.

### set\_export\_distribution

This command sets the relative weight with which the fuel production of the producer is exported to a given port.

The weights of all ports are normalized to sum to one in every time-step, so a weight is a share of the production only when the weights assigned across the ports already sum to one. Assigning `0.5` to one of three ports therefore exports the entire production to that port, not half of it. If no port carries a positive weight, the production is split equally across all ports.

* **Primary key type**: String (Port name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"port_name", 0.2`
  + `"port_name", Forecast("name")`
* **Unit**: Relative weight
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0, which leaves the production split equally across all ports when no port is weighted.
