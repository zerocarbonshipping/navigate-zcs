<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Levy

A `Levy` node defines a regulatory measure that works on a per ton of emissions basis. Examples of levies are
CO<sub>2</sub>-taxes and subsidy schemes.

Example:

```python
Levy "regional_carbon_tax" {
    Scheme = PENALTY
    Scope = WTW
    Fuels = Fuel("*")
    Emissions = Emission("*")
    EmissionsLifetime = 100
    
    Jurisdiction = [Port("europe")]
    
    Level = 200
}
```
## Attributes

### Active

This attribute sets whether the levy is active in the current time-step. This attribute can be changed during the `EVENTS` simulation to either introduce a levy assuming there was no foresight to its implementation or to discontinue an already existing levy.

* **Data type**: `Boolean`
* **Default**: TRUE

### Scheme 

This attribute sets the scheme of the levy. Specifically whether it penalizes emissions above the threshold, subsidises emissions below, or both.

* **Data type**: `ID`
* **Legal values**: [LevySchemeID](appendix_ids.md#levyschemeid)
* **Default**: None. Must be provided by the user.

### Jurisdiction 

This attribute defines a list of ports that are under the jurisdiction of the policy.

* **Data type**: List of `Port` nodes
* **Example values**:
  + `[Port("name1"), Port("name2")]`
  + `[Port("*")]`
* **Default**: None. Must be provided by the user.

### Emissions 

This attribute specifies the emission(s) being targeted by the policy. Use the wildcard `Emission("*")` to target every emission defined in the simulation.

* **Data type**: List of `Emission` nodes
* **Example values**:
  + `Emission("name")`
  + `[Emission("name_1"), Emission("name_2")]`
  + `Emission("*")`
* **Default**: None. Must be provided by the user.

### Fuels 

This attribute specifies the fuel(s) being targeted by the policy. This can be used to e.g., limit a subsidy scheme to only subsidize e-fuels. Use the wildcard `Fuel("*")` to target every fuel defined in the simulation.

* **Data type**: List of `Fuel` nodes
* **Example values**:
  + `Fuel("name")`
  + `[Fuel("name_1"), Fuel("name_2")]`
  + `Fuel("*")`
* **Default**: None. Must be provided by the user.

### Scope

This attribute defines the scope of emission targeted by the policy.

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

This attribute defines whether emissions slip is included in the calculation of the emissions in the levy.

* **Data type**: `Boolean`
* **Default**: TRUE

### Level

This attribute determines the level of the penalty or subsidy proportional to the fuels absolute difference from the threshold.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**: `100`
* **Unit**: USD/ton emission
* **Minimum value**: 0
* **Default**: 0

### LowerThreshold

This attribute sets the lower emission intensity threshold of the levy. If ‘Scheme’ is SUBSIDY or BOTH, then values below the threshold are subsidized, if set to PENALTY or BOTH, then values above the threshold are penalized.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `40`
  + `Forecast("name")`
* **Minimum value**: 0
* **Unit**: kg emission / GJ
* **Default**: 0

### UpperThreshold

This attribute sets the upper emission intensity threshold of the levy. The penalty is only paid for emissions between the lower and upper threshold. If not set, there is no upper cap on the penalty. Only relevant for ‘PENALTY’ and ‘BOTH’ schemes.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `91.2`
  + `Forecast("name")`
* **Minimum value**: 0
* **Unit**: kg emission / GJ
* **Default**: None (no upper cap)

## Commands

### set\_include\_vessel

This command allows the user to include or exclude certain vessels from the levy.

* **Primary key type**: String (Vessel name)
* **Data type**: `Boolean`
* **Default**: TRUE

### set\_global\_warming\_potential

This command allows the user to set the global warming potential (GWP) for a specific emission. If the GWP is assigned on the levy then it overwrites the physical GWP defined on the emission during the calculation of emission factors.

* **Primary key type**: String (Emission name)
* **Data type**: `Float`, `Curve`, `Variable`
* **Example values**:
  + `"emission_name", 25`
  + `"emission_name", Curve("name")`
* **Unit**: ton CO<sub>2</sub>eq/ton emission
* **Default**: The physical global warming potential assigned to the specific emissions

### set\_fuel\_wtt

This command allows the user to set the WTT (Well-to-Tank) emission factor for a given fuel and emission as it is defined under a certain policy. If these emission factor values are assigned under a levy, they override the emission factor values that are otherwise used in Navigate

* **Primary key type**: String (Fuel name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 3.2`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: Determined through internal calculations

### set\_fuel\_ttw

This command allows the user to set the TTW (Tank-to-Wake) emission factor for a given fuel and emission as it is defined under a certain policy. If these emission factor values are assigned under a levy, they override the emission factor values that are otherwise used in Navigate

* **Primary key type**: String (Fuel name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 3.2`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: Determined through internal calculations
