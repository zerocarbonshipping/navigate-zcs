<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Port

A `Port` node defines a port in which a vessel can bunker fuel. Port nodes are often defined as a region in
which the vessel is operating. Examples of ports are Rotterdam (if used specifically) and Asia
(if used regionally). A port participates in the simulation only when a `Route`'s `Ports` lists it; an
unrouted port is removed (see [Unreachable nodes](dsl_reference.md#unreachable-nodes)).

Example:

```python
Port "asia" {
    ShorePowerPrice = 80
    ShorePowerAvailability = 0.8
    
    set_fuel_price("low_sulfur_fuel_oil", 250)
    set_fuel_wtt("low_sulfur_fuel_oil", "carbon_dioxide", 0.62)
}
```

## Attributes

### ShorePowerPrice

This attribute sets the price of shore power electricity in the port in currency/MWh. It is converted internally to currency/GJ for consistency with the energy model.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `80`
  + `Forecast("name")`
* **Unit**: currency/MWh
* **Minimum value**: 0
* **Default**: 0

### ShorePowerAvailability

This attribute sets the fraction of the time in port during which a shore power connection is available. A value of 0 means shore power is not available in the port. A vessel's shore power use in the port is capped at this share of its time in port, times the lesser of a technology package's combined `ShorePowerCapacity` and the electrical load in port with that package, averaged over the vessels by the packages they carry.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.8`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

## Commands

### set\_allow\_bunkering

This command sets whether it is allowed to bunker a specific fuel in the port.

A Producer's export aimed at a port that does not allow the fuel goes to the ports that allow it, by their export weights.

* **Primary key type**: String (Fuel name; supports wildcards)
* **Data type**: `Boolean`
* **Example values**:
  + `"fuel_name", TRUE`
  + `"fuel_name", FALSE`
* **Default**: TRUE

### set\_handling\_cost

This command sets the costs related to storage and the service of bunkering of a specific fuel in the port in currency/ton.

* **Primary key type**: String (Fuel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 50`
  + `"fuel_name", Forecast("name")`
* **Unit**: currency/ton
* **Minimum value**: 0
* **Default**: 0

### set\_bunkering\_limit

This command sets a limitation for the amount of fuel that can be bunkered in the port in tons/year.

A Producer's fuel imported above the limit is redistributed to the other ports allowed to bunker it, in proportion to how far each is under its own limit; a port the producer sends no fuel to receives no share. Any surplus the limited ports cannot absorb is split equally across the ports with no limit set, and dropped where none exist. A liquid-market fuel is unaffected: its supply is the limit itself. `INF` means no limit.

* **Primary key type**: String (Fuel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 1e6`
  + `"fuel_name", Forecast("name")`
* **Unit**: tons/year
* **Minimum value**: 0
* **Default**: Not set. Bunkering of the fuel is unlimited, as with `INF`.

### set\_bunkering\_inertia

This command sets the inertia of a fuel being bunkered in fraction/year.

The inertia refers to the fraction of the amount bunkered in the previous time-step that must at minimum be bunkered in the current time-step.

* **Primary key type**: String (Fuel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 0.66`
  + `"fuel_name", Forecast("name")`
* **Unit**: fraction/year
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### set\_fuel\_price

This command sets the price of a specific fuel in the port in currency/ton.

Where it is set, it takes the place of the price calculated bottom-up from production. A liquid-market fuel has no production, so this is its only price. The bunker price is this price plus the [handling cost](#set_handling_cost).

* **Primary key type**: String (Fuel name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 600`
  + `"fuel_name", Forecast("name")`
* **Unit**: currency/ton
* **Minimum value**: 0
* **Default**: Not set. The price is calculated bottom-up from production; for a liquid-market fuel it is 0.

### set\_fuel\_wtt

This command sets the WTT emissions of a specific fuel and emission in the port in ton emission/ton fuel.

Where it is set, it takes the place of the WTT emissions calculated bottom-up from production. A liquid-market fuel has no production, so this is its only WTT.

It is also the WTT that regulations and levies assume for the fuel bunkered at this port, unless the policy sets its own with its `set_fuel_wtt` ([Levy](levy.md#set_fuel_wtt), [Regulation](regulation.md#set_fuel_wtt)).

* **Primary key type**: String (Fuel name; supports wildcards)
* **Secondary key type**: String (Emission name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 600`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission / ton fuel
* **Default**: Not set. The WTT emissions are calculated bottom-up from production; for a liquid-market fuel they are 0.

### set\_shore\_power\_wtt

This command sets the WTT (Well-to-Tank) emissions of the shore power grid electricity for a specific emission in the port in ton emission/MWh. It is converted internally to ton emission/GJ. The grid emits upstream of the vessel, so regulations and levies count these emissions as WTT: one with `Scope = TTW` counts none of them.

* **Primary key type**: String (Emission name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"emission_name", 0.18`
  + `"emission_name", Forecast("name")`
* **Unit**: ton emission/MWh
* **Minimum value**: 0
* **Default**: 0
