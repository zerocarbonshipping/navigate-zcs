<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Port

A `Port` node defines a port in which a vessel can bunker fuel. Port nodes are often defined as a region in
which the vessel is operating. Examples of ports are Rotterdam (if used specifically) and Asia
(if used regionally).

Example:

```python
Port "asia" {
    WindUtilization = 0.4
    SolarUtilization = 0.4
    
    set_bunker_price_overwrite("low_sulfur_fuel_oil", 250)
    set_bunker_wtt_overwrite("low_sulfur_fuel_oil", "carbon_dioxide", 0.62)
}
```

## Attributes

### WindUtilization

This attribute sets the wind utilization factor in the port. The wind utilization is used for alternative power in port.

This is relevant only for vessels that have alternative power technologies utilizing wind energy installed. These technologies have an installed capacity. The parameter "wind utilization" describes the fraction of this installed capacity that is eventually utilized while in port. E.g. if the wind is only blowing half of the time while in port, 50% of the installed capacity is utilized.

* **Data type**: `Float`
* **Example values**: `0.5`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

### SolarUtilization

This attribute determines the solar utilization factor in the port. The solar utilization is used for alternative power in port.

This is relevant only for vessels that have alternative power technologies utilizing solar energy installed. These technologies have an installed capacity. The attribute "solar utilization" describes the fraction of this installed capacity that is eventually utilized while in port. E.g., if the sun is only shining half of the time while in port, 50% of the installed capacity is utilized.

* **Data type**: `Float`
* **Example values**: `0.5`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1

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
