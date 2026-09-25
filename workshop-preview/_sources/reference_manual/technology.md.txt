<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Technology

A 'Technology' node defines a device or operational approach that improves the efficiency of a vessel, provides an alternative power source or offers a power transfer from one energy type to another. 
Examples are air lubrication,  wind assisted propulsion or shaft generators respectively.

Example:

```python
Technology "air_lubrication" {
	CAPEX = 2.5e6
	OPEX = 30e3

    set_energy_saving(PROPULSION, 0.04)
}
```

## Attributes

### CAPEX

This attribute represents the CAPEX (capital expenditure) for installing the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `2.5e6`
  + `Forecast("name")`
* **Unit**: USD
* **Minimum value**: 0
* **Default**: 0

### OPEX

This attribute represents the OPEX (operational expenditure) for maintaining the machinery annually.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `30e3`
  + `Forecast("name")`
* **Unit**: USD/year
* **Minimum value**: 0
* **Default**: 0

### Lifetime

This attribute sets the lifetime of the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `25`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: Vessel lifetime.

### Replacement

This attribute sets the fraction of CAPEX paid when part of the machinery is replaced at the end of the part’s lifetime.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Default**: 1

### ShorePowerCapacity

This attribute sets the vessel-side shore power connection capacity.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `4.0`
  + `Forecast("name")`
* **Unit**: MW
* **Minimum value**: 0
* **Default**: 0

## Commands

### set\_energy\_saving
This command sets the fraction of energy saved by the technology.

* **Primary key type**: [EnergyDemandTypeID](appendix_ids.md#energydemandtypeid)
* **Data type**: `Float`, `Variable`
* **Example value**:
  + `PROPULSION, 0.2`
  + `HEAT, Variable("name")`
* **Unit**: Fraction
* **Minimum value**: 0

### set\_external\_power
This command sets the external power provided by the technology.

* **Primary key type**: [EnergyDemandTypeID](appendix_ids.md#energydemandtypeid)
* **Data type**: `Float`, `Variable`
* **Example value**:
  + `PROPULSION, 1.25`
  + `HEAT, Variable("name")`
* **Unit**: MW
* **Minimum value**: 0

### set\_power\_transfer
This command sets the power transfer from one energy type to another.

* **Primary key type**: [EnergyDemandTypeID](appendix_ids.md#energydemandtypeid)
* **Data type**: `Float`, `Variable`
* **Example value**:
  + `PROPULSION, 1.25`
  + `HEAT, Variable("name")`
* **Unit**: MW
* **Minimum value**: 0
