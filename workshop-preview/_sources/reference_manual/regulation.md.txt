<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Regulation

A `Regulation` node defines a regulatory measure that works on yearly emissions of a vessel. Examples of
regulations are goal-base fuel standards (such as the IMO Net-Zero Framework and FuelEU Maritime) and 
transport based regulation such as the IMO CII regulation.

Example:

```python
Regulation "cii" {
	Measure = TRANSPORT_NOMINAL
	Scheme = INDIVIDUAL

	Scope = TTW
	IncludeSlip = FALSE

	Emissions = Emission("carbon_dioxide")
	Fuels = Fuel("*")
	
	Jurisdiction = [Port("africa"), Port("americas"), Port("asia"), Port("europe"), Port("middle_east")]
	
	RemedialCost = 0
}
```

## Attributes

### Active

This attribute sets whether the regulation is active in the current time-step. This attribute can be changed during the `EVENTS` simulation to either introduce a regulation assuming there was no foresight to its implementation or to discontinue an already existing regulation.

* **Data type**: `Boolean`
* **Default**: TRUE

### Scheme 

This attribute sets the scheme of the regulation. Specifically whether it allows trading of emission certificates or not.

* **Data type**: `ID`
* **Legal values**: [RegulationSchemeID](appendix_ids.md#regulationschemeid)
* **Default**: None. Must be provided by the user.

### Jurisdiction 

This attribute defines a list of ports that are under the jurisdiction of the regulation.

* **Data type**: List of `Port` nodes
* **Example values**:
  + `[Port("name1"), Port("name2")]`
  + `[Port("*")]`
* **Default**: None. Must be provided by the user.

### Emissions 

This attribute specifies the emission(s) being targeted by the regulation. Use the wildcard `Emission("*")` to target every emission defined in the simulation.

* **Data type**: List of `Emission` nodes
* **Example values**:
  + `Emission("name")`
  + `[Emission("name_1"), Emission("name_2")]`
  + `Emission("*")`
* **Default**: None. Must be provided by the user.

### Fuels 

This attribute specifies the fuel(s) being targeted by the regulation. Use the wildcard `Fuel("*")` to target every fuel defined in the simulation.

* **Data type**: List of `Fuel` nodes
* **Example values**:
  + `Fuel("name")`
  + `[Fuel("name_1"), Fuel("name_2")]`
  + `Fuel("*")`
* **Default**: None. Must be provided by the user.

### Scope

This attribute defines the scope of emission targeted by the regulation.

* **Data type**: `ID`
* **Legal values**: [PolicyScopeID](appendix_ids.md#policyscopeid)
* **Default**: WTW

### EmissionsLifetime

This attribute determines the emissions lifetime used in the GWP (Global Warming Potential) calculation of emissions.

* **Data type**: `Float`, `Variable`
* **Example values**: `20`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 100

### IncludeSlip

This attribute defines whether emissions slip is included in the calculation of the emissions in the regulation.

* **Data type**: `Boolean`
* **Default**: TRUE

### Measure 

This attribute sets the emission measure of the regulation.

If 'ABSOLUTE' the absolute emissions in tons/year are targeted.
If 'INTENSITY' the emission intensity in kg/GJ are targeted.
If 'TRANSPORT\_NOMINAL' the carbon intensity index in CO<sub>2</sub>-eq/nominal cargo-miles is targeted.
If 'TRANSPORT' the carbon intensity index in CO<sub>2</sub>-eq/actual cargo-miles is targeted.

* **Data type**: `ID`
* **Legal values**: [RegulationMeasureID](appendix_ids.md#regulationmeasureid)
* **Unit**: Different units depending on the value of ‘Measure’
  + ABSOLUTE: ton emissions
  + INTENSITY: kg emissions / GJ
  + TRANSPORT\_NOMINAL: g emissions / nominal cargo miles
  + TRANSPORT: g emissions / actual cargo miles
* **Default**: None. Must be provided by the user

### IntraFraction

This attribute sets the fraction for how much of the emissions between two ports inside (intra) the jurisdiction should be counted in the calculation.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Minimum value**: 0
* Maxiumum value: 1
* **Unit**: Fraction of emissions counted during intra jurisdiction travel
* **Default**: 1

### InterFraction

This attribute sets the fraction for how much of the emissions between two ports where one is in the jurisdiction and the other outside the
jurisdiction (inter) should be counted in the calculation.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### ExtraFraction

This attribute sets the fraction for how much of the emissions between two ports outside the jurisdiction (extra) should be counted in the calculation.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### RemedialCost

This attribute sets the level of the regulation being paid or received dependent on the scheme in USD/ton emission.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `500`
  + `Forecast("name")`
* **Unit**: USD/ton emission
* **Minimum value**: 0
* **Default**: 0

## Commands

### set\_global\_warming\_potential

This command allows the user to set the global warming potential (GWP) for a specific emission. If the GWP is assigned on the regulation then it overwrites the physical GWP defined on the emission during the calculation of emission factors.

* **Primary key type**: String (Emission name)
* **Data type**: `Float`, `Curve`, `Variable`
* **Example values**:
  + `"emission_name", 25`
  + `"emission_name", Curve("name")`
* **Unit**: ton CO<sub>2</sub>eq/ton emission
* **Default**: The physical global warming potential assigned to the specific emissions

### set\_include\_vessel

This command allows the user to include or exclude certain vessels from the regulation.

* **Primary key type**: String (Vessel name)
* **Data type**: `Boolean`
* **Default**: TRUE

### set\_fuel\_wtt

This command allows the user to set the WTT (Well-to-Tank) emission factor for a given fuel and emission as it is defined under a certain policy. If these emission factor values are assigned under a regulation, they override the emission factor values that are otherwise used in Navigate

* **Primary key type**: String (Fuel name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 3.2`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: Determined through internal calculations (a supply-weighted average of the production-based bunker WTT across the jurisdiction ports on the vessel's route; ports without supply of the fuel carry no weight)

### set\_fuel\_ttw

This command allows the user to set the TTW (Tank-to-Wake) emission factor for a given fuel and emission as it is defined under a certain policy. If these emission factor values are assigned under a regulation, they override the emission factor values that are otherwise used in Navigate

* **Primary key type**: String (Fuel name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 3.2`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: Determined through internal calculations

### set\_vessel\_threshold

This command sets the threshold that a specific vessel must satisfy in the measure unit. Every vessel included in the regulation must have a threshold; use the wildcard `"*"` to assign the same threshold to all vessels. If ‘Scheme’ is FLEXIBLE the per-vessel thresholds pool into a single fleet-level constraint.

* **Primary key type**: String (Vessel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name", 90`
  + `"*", Forecast("name")`
* **Unit**: Different units depending on the value of ‘Measure’
  + ABSOLUTE: ton emissions
  + INTENSITY: kg emissions / GJ
  + TRANSPORT\_NOMINAL: g emissions / nominal cargo miles
  + TRANSPORT: g emissions / actual cargo miles
* **Minimum value**: 0
* **Default**: None

### set\_vessel\_capacity

This command sets the capacity of a specific vessel for use in transport calculations.

This is only relevant if 'Measure' is set to 'TRANSPORT\_NOMINAL' or 'TRANSPORT'.

* **Primary key type**: String (Vessel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name", 75000`
  + `"vessel_name", Forecast("name")`
* **Minimum value**: 0
* **Default**: None
