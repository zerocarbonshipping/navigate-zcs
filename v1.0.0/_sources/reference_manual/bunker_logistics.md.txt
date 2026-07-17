<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# BunkerLogistics

The `BunkerLogistics` general node allows configuration of cost and emissions related to transport of fuel
between production and bunkering hubs. Further it defines which fuels belong to a liquid market and thus are
not subject to bottom-up modeling of cost, availability, etc.

Example:

```python
BunkerLogistics {
    LiquidMarketFuels = [Fuel("low_sulfur_fuel_oil"), Fuel("liquefied_natural_gas")]

    set_distance("africa", "europe", 1000)
    set_transport_cost("methanol_electro", 1.5)
    set_transport_wtt("methanol_electro", "carbon_dioxide", 1.5)
}
```

## Attributes

### LiquidMarketFuels

This attribute sets the list of fuels that exist and belong to a liquid market.

Fuels that belong to a liquid market cannot be modeled bottom-up via Plant and Producer nodes but require
manual assignment of supply, price, and WTT emissions at the Port level. Liquid market fuels are defined by not being supply constrained but available in the necessary quantities.

* **Data type**: List of `Fuel` nodes
* **Example value**:
  + `[Fuel("name")]`
  + `[Fuel("name1"), Fuel("name2")]`
  + `[Fuel("*")]`
* **Default**: None.

## Commands

### set\_distance

This command sets the distance between a region and a port in nautical miles.

* **Primary key type**: String (Region name)
* **Secondary key type**: String (Port name)
* **Data type**: `Float`
* **Example value**:
  + `"region_name", "port_name", 1000`
* **Unit**: nautical miles
* **Minimum value**: 0
* **Default**: 0

### set\_transport\_cost

This command sets the cost of transporting a fuel in ton USD/ton/nautical-mile.

* **Primary key type**: String (Fuel name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example value**:
  + `"fuel_name", 1.5`
  + `"fuel_name", Forecast("name")`
* **Unit**: USD / ton / nautical mile
* **Minimum value**: 0
* **Default**: 0

### set\_transport\_wtt

This command sets the emission WTT for transporting a fuel per nautical mile.

* **Primary key type**: String (Fuel name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example value**:
  + `"fuel_name", "emission_name", 1.5`
  + `"fuel_name", "emission_name", Forecast("name")`
* **Unit**: ton emission / ton-nautical miles
* **Minimum value**: 0
* **Default**: 0
