<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Plant

A `Plant` node defines a fuel production plant which is part of the modeling of the available fuel supply.
Examples of plants are e-methanol plants and blue ammonia plants.

Example:

```python
Plant "plant_methanol_electro" {
    Fuel = Fuel("methanol_electro")
    Process = Process("methanol_synthesis_electro")
    Region = Region("europe")
    Source = Source("grid")
    
    Capacity = Forecast("methanol_electro_plant_capacity")
    
    LeadTime = 3
    Lifetime = 20
    Uptime = 0.9
}
```


## Attributes

### Fuel 

This attribute sets the fuel that is produced by the plant.

* **Data type**: `Fuel` node
* **Example value**: `Fuel("name")`
* **Default**: None. Must be provided by the user.

### Process 

This attribute sets the production process used by the plant.

* **Data type**: `Process` node
* **Example value**: `Process("name")`
* **Default**: None. Must be provided by the user.

### Region 

This attribute sets the region in which the plant is built.

* **Data type**: `Region` node
* **Example value**: `Region("name")`
* **Default**: None. Must be provided by the user.

### Source 

This attribute sets the energy source which is used to generate power for the plant.

* **Data type**: `Source` node
* **Example value**: `Source("name")`
* **Default**: None. Must be provided by the user.

### Capacity 

This attribute sets the production capacity of the plant in tons/day. `INF` is rejected.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `3000`
  + `Forecast("name")`
* **Unit**: tons / day
* **Minimum value**: >0
* **Default**: None. Must be provided by the user.

### Uptime

This attribute sets the production uptime of the plant in time/time.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.95`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: >0
* **Maximum value**: 1
* **Default**: 1

### Lifetime

This attribute sets the lifetime of the plant in years.

The plant is decommissioned when it surpasses its lifetime.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example value**: `30`
* **Unit**: Years
* **Minimum value**: >0
* **Default**: 30

### LeadTime

This attribute sets the planning to production lead time of the plant in years.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `4`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 1

### CostOfCapital

This attribute sets the cost of capital used to calculate the costs associated with financing the investment (through debt and equity) as well as the discount rate used in calculating the levelized costs of production and delivery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.1`
  + `Forecast("name")`
* **Unit**: Fraction/year
* **Minimum value**: 0
* **Default**: 0

## Commands

### set\_feed\_transport

This command sets the transport mode used for transporting a specific feedstock or process output to the plant.

* **Primary key type**: String (Name of feedstock or process; supports wildcards)
* **Data type**: `Transport` node
* **Example values**:
  + `"feedstock_name", Transport("name")`
  + `"process_name", Transport("name")`
* **Default**: Not set. The feed is not transported, so no transport cost or emissions accrue.

### set\_feed\_distance

This command sets the distance a given feedstock or process output is transported to the plant in nautical miles. A distance can only be assigned to a feed that is also assigned a transport with `set_feed_transport`.

* **Primary key type**: String (Name of feedstock or process; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"feedstock_name", 100`
  + `"process_name", 100`
  + `"process_name", Forecast("name")`
* **Unit**: nautical miles
* **Minimum value**: 0
* **Default**: 0 for a feed assigned a transport

### set\_fuel\_transport

This command sets the transport mode used for delivering the produced fuel to a given port. The cost and WTT emissions of the delivery are given by the transport rates of the plant's region, see `set_transport_cost` and `set_transport_wtt` on the [Region](region.md) node.

* **Primary key type**: String (Name of port; supports wildcards)
* **Data type**: `Transport` node
* **Example value**: `"port_name", Transport("name")`
* **Default**: Not set. The fuel is not transported to the port, so no delivery cost or emissions accrue.

### set\_fuel\_distance

This command sets the distance the produced fuel is transported to a given port in nautical miles. A distance can only be assigned to a port that is also assigned a transport with `set_fuel_transport`.

* **Primary key type**: String (Name of port; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"port_name", 100`
  + `"port_name", Forecast("name")`
* **Unit**: nautical miles
* **Minimum value**: 0
* **Default**: 0 for a port assigned a transport
