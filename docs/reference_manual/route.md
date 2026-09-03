<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Route

A `Route` node defines the operational profile of a vessel. A route can either be specific with an ordered
list of visited ports (typical of liner shipping) or a more regional definition with a unordered list
(typical of tramp shipping). Examples of routes are Rotterdam-Singapore (if specific) and domestic in
Europe (if regional).

Example:

```python
Route "regional_route" {
    RouteType = REGIONAL_TRIP

    Ports = [Port("europe")]
    PortCalls = [10]
    
    TimeAtSea = 0.698
    ConditionDistribution = [0.5, 0.5]
    Speeds = [11.2, 13.6]
    CapacityUtilizations = [1.0, 0.0]
}
```

## Conditions

There are several conditions that must be met depending on whether the RouteType is defined as REGIONAL\_TRIP or ROUND\_TRIP.

If RouteType is defined as ROUND\_TRIP:

* Several attributes under the node ‘Route’ are irrelevant (TimeAtSea, PortCalls, Times).
* Values for following attributes must be provided by the user: PortDurations, Distances.
* The number of defined Distances and Speeds must correspond.
* A minimum of 2 ports must be assigned.
* The number of defined Distances and Ports must correspond.
* The number of defined Ports and PortDurations must correspond.
* It is not possible to place a port after itself in the sequential list, i.e., the same port cannot be visited a second time directly after itself.
* The same port cannot be placed both first and last, because the set of ports is assumed to wrap around.

If RouteType is defined as REGIONAL\_TRIP:

* Several attributes under the node ‘Route’ are irrelevant (Distances, PortDurations)
* Values for TimeAtSea must be provided by the user.
* The number of defined Times and Speeds must correspond.
* All ports must be unique.
* The number of defined Ports and PortCalls must correspond.

## Attributes

### RouteType 

This attribute sets the route type to either ROUND\_TRIP or REGIONAL\_TRIP.

In a ROUND\_TRIP, the end port is the same as the start port. Additionally, *individual legs of the journey are specified*, allowing inputs for different distances, speeds, and capacity utilizations etc. on separate legs. These legs are *sequential*. This means that when the Ports are defined as the list [Port("name1"), Port("name2"), Port("name3")], then the route is specified as starting from Port("name1") to Port("name2") to Port("name3") to ending at Port("name1"). Ports can be visited more than once.

In a REGIONAL\_TRIP, *individual legs of the journey are not specified*. Instead, a distribution of fraction of time spent at different speeds and cargo capacity can be defined. This also means that there is no definition of a start or end port. Ports in the pool can also be visited more than once.

* **Data type**: `ID`
* **Legal values**: [RouteTypeID](appendix_ids.md#routetypeid)
* **Default**: None. Must be provided by user

### Ports 

This attribute sets the list of ports available for bunkering on the route. The number of ports and bunker regions must correspond. This is the only attribute that keeps a `Port` in the simulation — a port on no route is removed (see [Unreachable nodes](dsl_reference.md#unreachable-nodes)).

* **Data type**: List of `Port` nodes
* **Example values**:
    - [Port("name")]
    - [Port("name1"), Port("name2"), Port("name3")]
    - [Port("\*")]
* **Default**: None. Must be provided by user

### TimeAtSea 

This attribute sets the fraction of time spent at sea. This is only applicable if 'RouteType' is REGIONAL\_TRIP. Refer to the section ‘Conditions’.

* **Data type**: `Float`, `Forecast`, `Variable`
* Example vaues: 0.75
* **Unit**: Fraction of time spent at sea per total time
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: None. Must be provided by the user if RouteType is REGIONAL\_TRIP.

### PortDurations 

This attribute sets the duration spent at each port call of the trip in days. It is only applicable if 'RouteType' is ROUND\_TRIP. Refer to the section ‘Conditions’.

* **Data type**: List of `float`, `Forecast`, `Variable`
* **Example values**:
    - [3.5, 5]
    - [Forecast("name"), Variable("name")]
* **Unit**: Days
* **Minimum value**: 0
* **Default**: None. Must be provided by the user if RouteType is ROUND\_TRIP.

### PortCalls

This attribute sets the number of port calls per port over the reference duration. This is only applicable if 'RouteType' is REGIONAL\_TRIP. Refer to the section ‘Conditions’.

* **Data type**: List of `float`, `Forecast`, `Variable`
* **Example values**:
    - [20, 15.5]
    - [Forecast("name"), Variable("name")]
* **Unit**: Number of port calls per port over the reference duration
* **Minimum value**: 0
* **Default**: List of 0s (Number of 0s corresponding to the number of Ports).

### Distances 

This attribute sets the distance of the various legs of the trip in nautical miles. It is only applicable if RouteType is ROUND\_TRIP. Refer to the section ‘Conditions’.

* **Data type**: List of `Floats`
* **Example values**:
    - [1470, 150.8]
* **Unit**: Nautical Miles
* **Minimum value**: 0
* **Default**: None. Must be provided by the user if RouteType is ROUND\_TRIP.

### ConditionDistribution 

This attribute sets the fraction of time spent on the various legs of the trip. The sum of the coefficients in the list must equal 1. This is only applicable if 'RouteType' is REGIONAL\_TRIP. Refer to the section ‘Conditions’.

* **Data type**: List of `Floats`
* **Example values**:
    - [1]
    - [0.3, 0.7]
* **Unit**: Fraction of time spent on the various legs of the trip
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: None.

### Speeds 

This attribute sets the speed of the various legs of the trip in knots. The number of defined Speeds must be equal to the number of defined fractions for CapacityUtilizations, WindUtilizations, and SolarUtilizations, respectively – this corresponds to the number of legs of the trip. Also refer to the section ‘Conditions’.

* **Data type**: List of `Floats` OR `Forecasts` OR `Variables`
* **Example values**:
    - [12, 14]
    - [Forecast("name"), Variable("name")]
* **Unit**: Knots
* **Minimum value**: 0
* **Default**: None. Must be provided by the user.

### CapacityUtilizations

This attribute sets the cargo capacity utilization of the various legs of the trip. The number of defined CapacityUtilizations must be equal to the number of defined fractions for SolarUtilizations, WindUtilization, and defined Speeds, respectively – this corresponds to the number of legs of the trip. Also refer to the section ‘Conditions’.

* **Data type**: List of `Floats` OR `Forecasts` OR `Variables`
* **Example values**:
    - [1, 0]
    - [Forecast("name"), Variable("name")]
* **Unit**: Fraction of cargo capacity
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: List of 1s

### WindUtilizations

This attribute defines what fraction of the capacity of installed wind utilization technology is used on the various legs of the trip. The number of defined WindUtilizations must be equal to the number of defined fractions for CapacityUtilizations, SolarUtilization, and defined Speeds, respectively – this corresponds to the number of legs of the trip. Also refer to the section ‘Conditions’.

* **Data type**: List of `Floats`
* **Example values**:
    - [0.7]
    - [0.1, 0.5]
* **Unit**: Fraction of max. wind utilization capacity used
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: List of 1s

### SolarUtilizations

This attribute defines what fraction of the capacity of installed solar utilization technology is used on the various legs of the trip. The number of defined SolarUtilizations must be equal to the number of defined fractions for CapacityUtilizations, WindUtilizations, and defined Speeds, respectively – this corresponds to the number of legs of the trip. Also refer to the section ‘Conditions’.

* **Data type**: List of `Floats`
* **Example values**:
    - [0.7]
    - [0.1, 0.5]
* **Unit**: Fraction of max. solar utilization capacity used
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: List of 1s

## Commands

### set\_voyage\_distribution

This command sets the fraction of total sailing time spent traveling from 'port\_from' to 'port\_to'.

* **Primary key type**: String (Port name)
* **Secondary key type**: String (Port name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"port_name_from", "port_name_to", 0.5`
  + `"port_name_from", "port_name_to", Forecast("name")`
* **Unit**: Fraction
* **Default**: Determined through internal calculations.
