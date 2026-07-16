<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Converter

A `Converter` node defines a machinery that converts potential energy from fuels (or electricity) into
kinetic energy for propulsion, electricity, or heat. Examples of converters are internal combusion engines,
fuel cells, and motors.

Example:

```python
Converter "internal_combustion_engine" {
    MainFuelTypes = METHANE
    PilotFuelTypes = OIL
    
    PowerCapacity = 8
    MinimumPilotFuel = 0.01
    Efficiency = 0.51
    
    set_slip_fraction(METHANE, Forecast("converter_methane_slip"))
    
    CAPEX = 300000
    OPEX = 30000
}
```

## Attributes

### CAPEX

This attribute represents the CAPEX (capital expenditure) for installing the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1e6`
  + `Forecast("name")`
* **Unit**: USD/MW
* **Minimum value**: 0
* **Default**: 0

### OPEX

This attribute represents the OPEX (operational expenditure) for maintaining the machinery annually.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1e4`
  + `Forecast("name")`
* **Unit**: USD/MW/year
* **Minimum value**: 0
* **Default**: 0

### Lifetime

This attribute sets the lifetime of the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `25.0`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: Vessel lifetime.

### Replacement

This attribute sets the fraction of CAPEX paid when part of the machinery is replaced at the end of the part’s lifetime, e.g. replacing the stack of a fuel cell.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Default**: 1

### MinimumLoad

This attribute sets the minimum load as a fraction of power capacity.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.3`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: None

### PowerCapacity 

This attribute sets the power capacity of the Converter.

* **Data type**: `Float`
* **Example values**: `50`
* **Unit**: MW
* **Minimum value**: 0
* **Default**: None. Must be provided by the user.

### MainFuelTypes 

This attribute sets the main fuel types that the Converter can use. All 'MainFuelTypes' must be unique, i.e., a fuel type cannot be duplicated in the input list, e.g. [OIL, OIL, METHANOL]. At least one fuel type must be assigned.

* **Data type**: List of `IDs`
* **Legal values**: [FuelTypeID](appendix_ids.md#fueltypeid)
* **Example values**:
  + `METHANOL`
  + `[AMMONIA, HYDROGEN]`
* **Default**: None. Must be provided by the user.

### PilotFuelTypes

This attribute sets the pilot fuel types that a Converter can use. All 'PilotFuelTypes' must be unique. If PilotFuelTypes is defined by the user, at least one fuel type must be assigned.

* **Data type**: List of `IDs`
* **Legal values**: [FuelTypeID](appendix_ids.md#fueltypeid)
* **Example values**:
  + `OIL`
  + `[OIL, LPG]`
* **Default**: None.

### MinimumPilotFuel

This attribute sets the minimum fraction of pilot fuel required out of the total fuel in GJ per GJ.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.05`
  + `Forecast("name")`
* **Minimum value**: 0
* **Maximum value**: 1
* **Unit**: GJ/GJ
* **Default**: 0

### Efficiency 

This attribute sets the fraction of the potential energy that is converted to kinetic energy.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Minimum value**: 0
* **Maximum value**: 1
* **Unit**: GJ/GJ
* **Default**: None

## Commands

### set\_consumption\_ttw

This command sets the emissions in the converter as a fraction of the amount of total fuel consumption. Hence, the command must specify a) the fuel type, b) the emission type, c) the fraction tons of emissions per ton of fuel consumed. The command is used to define emissions which does not pertain to the stoichiometric combustion process, but are converter specific, e.g., NOx or SOx.

* **Primary key type**: ID ([FuelTypeID](appendix_ids.md#fueltypeid))
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `OIL, "nitrous_oxide", 0.001`
  + `OIL, "carbon_dioxide", Forecast("name")`
* **Unit**: Ton of emission / ton of fuel
* **Minimum value**: 0
* **Default**: 0

### set\_slip\_fraction

This command sets the fraction of fuel mass that escapes unburned (slip) when using a specific fuel type, e.g., methane slip. Hence, the command must specify a) the fuel type, b) the fraction of fuel mass escaping unburned.

* **Primary key type**: ID ([FuelTypeID](appendix_ids.md#fueltypeid))
* **Data type**: `Float`, `Variable`
* **Example values**:
  + `METHANE, 0.03`
  + `METHANE, Variable("methane_slip")`
* **Unit**: Ton of slip / ton of fuel
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0
