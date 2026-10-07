<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Technology

A `Technology` node defines a device or operational approach that improves the efficiency of a vessel, provides an alternative power source or offers a power transfer from one energy type to another.
Examples are air lubrication, wind assisted propulsion or shaft generators respectively.

Example:

```python
Technology "air_lubrication" {
	Capex = 2.5e6
	Opex = 30e3

    set_energy_saving(PROPULSION, 0.04)
}
```

## Attributes

### Capex

This attribute represents the CAPEX (capital expenditure) for installing the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `2.5e6`
  + `Forecast("name")`
* **Unit**: USD
* **Minimum value**: 0
* **Default**: 0

### Opex

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
* **Minimum value**: >0
* **Default**: Not set. The machinery lasts as long as the vessel it is installed on, with no replacement.

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

This attribute sets the vessel-side shore power connection capacity. A vessel's shore power use in a port is capped at the port's `ShorePowerConnectionShare` of its time in port, times the lesser of the combined capacity of its technologies and its electrical load in port.

* **Data type**: `Float`, `Variable`
* **Example values**:
  + `4.0`
  + `Variable("name")`
* **Unit**: MW
* **Minimum value**: 0
* **Default**: 0

## Commands

### set\_energy\_saving

This command sets the fraction of the raw energy demand of an energy demand type saved by the technology. The saving is applied before any external power is subtracted, and the savings of several technologies installed together compound: two savings of 0.1 give a combined saving of 1 − 0.9 × 0.9 = 0.19.

* **Primary key type**: [EnergyDemandID](appendix_ids.md#energydemandid) (supports wildcards)
* **Data type**: `Float`, `Variable`
* **Example values**:
  + `PROPULSION, 0.2`
  + `HEAT, Variable("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Default**: 0

### set\_external\_power

This command sets the external power the technology supplies to an energy demand type. The power is converted to energy over the time spent on each leg or in each port and subtracted from the demand left after the energy savings, floored at 0. The external powers of several technologies installed together add up.

* **Primary key type**: [EnergyDemandID](appendix_ids.md#energydemandid) (supports wildcards)
* **Data type**: `Float`, `Variable`
* **Example values**:
  + `PROPULSION, 1.25`
  + `HEAT, Variable("name")`
* **Unit**: MW
* **Minimum value**: 0
* **Default**: 0

### set\_power\_transfer

This command sets the power transferred from a source energy demand type to a sink energy demand type, e.g. from propulsion to electrical for a shaft generator. A Curve maps the load of the source's converter (its residual power divided by its power capacity) to the transferred power; a number is a constant power. The power is converted to energy over the time spent on each leg or in each port and subtracted from the sink's residual demand, floored at 0. The transfers of several technologies installed together add up.

* **Primary key type**: [EnergyDemandID](appendix_ids.md#energydemandid) (source; supports wildcards)
* **Secondary key type**: [EnergyDemandID](appendix_ids.md#energydemandid) (sink; supports wildcards)
* **Data type**: `Float`, `Curve`, `Variable`
* **Example values**:
  + `PROPULSION, ELECTRICAL, Curve("name")`
  + `PROPULSION, HEAT, 0.5`
* **Unit**: MW
* **Unit x**: Fraction of the source converter's power capacity (Curve)
* **Unit y**: MW (Curve)
* **Minimum value**: 0
* **Default**: 0
