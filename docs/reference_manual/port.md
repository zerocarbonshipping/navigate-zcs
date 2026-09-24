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
    ShorePowerCost = 80
    ShorePowerConnectionShare = 0.8
    
    set_bunker_price_overwrite("low_sulfur_fuel_oil", 250)
    set_bunker_wtt_overwrite("low_sulfur_fuel_oil", "carbon_dioxide", 0.62)
}
```

## Attributes

### ShorePowerCost

This attribute sets the shore power electricity tariff in the port in USD/MWh. It is converted internally to USD/GJ for consistency with the energy model.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `80`
  + `Forecast("name")`
* **Unit**: USD/MWh
* **Minimum value**: 0
* **Default**: 0

### ShorePowerConnectionShare

This attribute sets the fraction of the time in port during which a shore power connection is available. A value of 0 means shore power is not available in the port.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.8`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

## Commands

### set\_bunkering\_allowed

This command sets whether it is allowed to bunker a specific fuel in the port.

* **Primary key type**: String (Fuel name)
* **Data type**: `Boolean`
* **Example values**:
  + `"fuel_name", TRUE`
  + `"fuel_name", FALSE`
* **Default**: TRUE

### set\_handling\_cost

This command sets the costs related to storage and the service of bunkering of a specific fuel in the port in USD/ton.

* **Primary key type**: String (Fuel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 50`
  + `"fuel_name", Forecast("name")`
* **Unit**: USD/ton
* **Minimum value**: 0
* **Default**: 0

### set\_bunkering\_limit

This command sets a limitation for the amount of fuel that can be bunkered in the port in tons/year.

* **Primary key type**: String (Fuel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 1e6`
  + `"fuel_name", Forecast("name")`
* **Unit**: tons/year
* **Minimum value**: 0
* **Default**: INF

### set\_bunkering\_inertia

This command sets the inertia of a fuel being bunkered in fraction/year.

The inertia refers to the fraction of the amount bunkered in the previous time-step that must at minimum be bunkered in the current time-step.

* **Primary key type**: String (Fuel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 0.66`
  + `"fuel_name", Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### set\_bunker\_price\_overwrite

This command sets the price of a specific fuel in the port in USD/ton.

If an overwrite is set for a specific fuel, then the bottom-up calculation of production cost is ignored.

* **Primary key type**: String (Fuel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", 600`
  + `"fuel_name", Forecast("name")`
* **Unit**: USD/ton
* **Minimum value**: 0
* **Default**: None

### set\_bunker\_wtt\_overwrite

This command sets an overwrite of the WTT emissions for a specific fuel and emission in the port in ton emission/ton fuel.

If an overwrite is set for a specific fuel and emission, then the bottom-up calculation of production emissions is ignored.

* **Primary key type**: String (Fuel name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"fuel_name", "emission_name", 600`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission / ton fuel
* **Default**: None

### set\_shore\_power\_emission\_factor

This command sets the WTW (Well-to-Wake) emission factor of the shore power grid electricity for a specific emission in the port in ton emission/MWh. It is converted internally to ton emission/GJ.

* **Primary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"emission_name", 0.18`
  + `"emission_name", Forecast("name")`
* **Unit**: ton emission/MWh
* **Minimum value**: 0
* **Default**: 0
