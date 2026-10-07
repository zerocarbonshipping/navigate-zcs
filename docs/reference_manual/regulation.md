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

This attribute sets whether the regulation is active in the current time-step. An inactive regulation is ignored in both the expectations and the results. This attribute can be changed during the `EVENTS` simulation to either introduce a regulation assuming there was no foresight to its implementation or to discontinue an already existing regulation.

* **Data type**: `Boolean`
* **Default**: TRUE

### Scheme 

This attribute sets the scheme of the regulation. Specifically whether it allows trading of emission certificates or not.

* **Data type**: `ID`
* **Legal values**: [RegulationSchemeID](appendix_ids.md#regulationschemeid)
* **Default**: None. Must be provided by the user.

### Jurisdiction 

This attribute defines a list of ports that are under the jurisdiction of the regulation. Only ports assigned to a `Route` participate in the simulation; a listed port on no route is removed from the simulation and from this list with a warning (see [Unreachable nodes](dsl_reference.md#unreachable-nodes)).

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
* **Example value**: `20`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: Not set. The `EmissionsLifetime` of the [ModelDefinition](model_definition.md) is used.

### IncludeSlip

This attribute defines whether emissions slip is included in the calculation of the emissions in the regulation.

* **Data type**: `Boolean`
* **Default**: TRUE

### Measure 

This attribute sets the emission measure of the regulation.

If 'ABSOLUTE' the absolute emissions in tons/year are targeted.
If 'INTENSITY' the emission intensity in kg/GJ is targeted, per GJ of effective energy, (1 − slip) · LHV: the lower heating value of the fuel net of the fraction the converter burning it lets escape unburned (`set_slip_fraction` on the `Converter`).
If 'TRANSPORT\_NOMINAL' the carbon intensity index in g CO<sub>2</sub>-eq/nominal cargo-miles is targeted.
If 'TRANSPORT' the carbon intensity index in g CO<sub>2</sub>-eq/actual cargo-miles is targeted.

* **Data type**: `ID`
* **Legal values**: [RegulationMeasureID](appendix_ids.md#regulationmeasureid)
* **Unit**: Different units depending on the value of ‘Measure’
  + ABSOLUTE: ton emissions/year
  + INTENSITY: kg emissions / GJ
  + TRANSPORT\_NOMINAL: g emissions / nominal cargo miles
  + TRANSPORT: g emissions / actual cargo miles
* **Default**: None. Must be provided by the user.

### IntraFraction

This attribute sets the fraction for how much of the emissions between two ports inside (intra) the jurisdiction should be counted in the calculation.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
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

This attribute sets the cost of a remedial compliance unit. A vessel that does not meet its threshold, or under a FLEXIBLE scheme the pooled fleet, buys remedial units at this cost to cover the shortfall. Remedial units are only bought, never sold; under a FLEXIBLE scheme the remedial cost also caps the price of the flexibility units traded between vessels.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `500`
  + `Forecast("name")`
* **Unit**: USD/ton emission
* **Minimum value**: 0
* **Default**: 0

### FlexibilityHorizon

This attribute sets the decision horizon, in years, used to smooth the belief of the flexibility cost that enters the expected policy expenses of the policed vessels. It only applies when 'Scheme' is FLEXIBLE; assigning it under any other scheme is unused and logged as a warning.

A longer horizon makes the belief respond more slowly to changes in the flexibility cost between outer time-steps, preventing small changes in future fuel availability from translating into expectations of large flexibility-cost differences.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `3.0`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 3

### AllowThresholdAdjustment

This attribute sets whether the regulation threshold is automatically adjusted when the bunker algorithm detects non-compliance. If enabled, the bunker algorithm performs a multi-step solve where it first solves normally, then adjusts the threshold to match achievable compliance levels, and re-solves with the adjusted thresholds.

* **Data type**: `Boolean`
* **Default**: FALSE

## Commands

### set\_global\_warming\_potential

This command allows the user to set the global warming potential (GWP) for a specific emission. If the GWP is assigned on the regulation then it overwrites the physical GWP defined on the emission during the calculation of emission factors. A `Curve` is read at the emissions lifetime, like the GWP of the emission: the `EmissionsLifetime` of the regulation if assigned, otherwise that of the model.

* **Primary key type**: String (Emission name; supports wildcards)
* **Data type**: `Float`, `Curve`, `Variable`
* **Example values**:
  + `"emission_name", 25`
  + `"emission_name", Curve("name")`
* **Unit**: ton CO<sub>2</sub>eq/ton emission
* **Default**: Not set. The global warming potential assigned on the `Emission` is used.

### set\_include\_vessel

This command allows the user to include or exclude certain vessels from the regulation. Vessels are excluded unless included explicitly, e.g. with `set_include_vessel("*", TRUE)`.

* **Primary key type**: String (Vessel name; supports wildcards)
* **Data type**: `Boolean`
* **Example values**:
  + `"vessel_name", TRUE`
  + `"*", TRUE`
* **Default**: FALSE

### set\_fuel\_wtt

This command allows the user to set the WTT (Well-to-Tank) emission factor for a given fuel and emission as it is defined under a certain policy. If these emission factor values are assigned under a regulation, they override the emission factor values that are otherwise used in Navigate.

* **Primary key type**: String (Fuel name; supports wildcards)
* **Secondary key type**: String (Emission name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 3.2`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: Not set. The WTT emission factor is averaged over the ports of the vessel's route, using each port's `set_bunker_wtt_overwrite` if assigned, otherwise an estimate from the plants producing the fuel.

### set\_fuel\_ttw

This command allows the user to set the TTW (Tank-to-Wake) emission factor for a given fuel and emission as it is defined under a certain policy. If these emission factor values are assigned under a regulation, they override the emission factor values that are otherwise used in Navigate.

* **Primary key type**: String (Fuel name; supports wildcards)
* **Secondary key type**: String (Emission name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 3.2`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: Not set. The TTW emission factor is calculated per converter from the fuel's TTW emission factor and the converter's slip fraction and consumption emissions.

### set\_vessel\_threshold

This command sets the threshold that a specific vessel must satisfy in the measure unit. Every vessel included in the regulation must have a threshold; use the wildcard `"*"` to assign the same threshold to all vessels. If ‘Scheme’ is FLEXIBLE the per-vessel thresholds pool into a single fleet-level constraint.

* **Primary key type**: String (Vessel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name", 90`
  + `"*", Forecast("name")`
* **Unit**: Different units depending on the value of ‘Measure’
  + ABSOLUTE: ton emissions/year
  + INTENSITY: kg emissions / GJ
  + TRANSPORT\_NOMINAL: g emissions / nominal cargo miles
  + TRANSPORT: g emissions / actual cargo miles
* **Minimum value**: 0
* **Default**: None. Must be provided by the user for every vessel included in the regulation.

### set\_vessel\_capacity

This command sets the capacity of a specific vessel for use in transport calculations.

This is only relevant if 'Measure' is set to 'TRANSPORT\_NOMINAL' or 'TRANSPORT'.

* **Primary key type**: String (Vessel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"vessel_name", 75000`
  + `"vessel_name", Forecast("name")`
* **Unit**: Same as the vessel's `NominalCapacity` (e.g., TEU, CEU, dwt)
* **Minimum value**: 0
* **Default**: Not set. The vessel's `NominalCapacity` is used.
