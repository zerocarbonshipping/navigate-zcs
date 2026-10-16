<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Route

A `Route` node defines the operational profile of a vessel: the ports it calls at, the legs it sails between them, and the speed, cargo utilization and time in port on each leg. A port often stands for a whole region, such as Europe or Asia.

A route is one of two types, set by [RouteType](#routetype):

* A `LINER` route lists its ports in the order they are called and describes one voyage around them, with the distance of each leg and the time spent in port after it.
* A `TRAMP` route lists a pool of ports and describes a year of operation: the share of the year spent at sea, how the sea miles split between the legs, and how often each port is called.

The names describe the calculation, not the market segment. A segment that trades on liner schedules, such as container shipping, may well be modelled as a `TRAMP` route, and the default routes shipped with Navigate are all `TRAMP` routes.

LINER example:

```python
Route "asia_europe_loop" {
    RouteType = LINER
    Ports = [Port("port_asia"), Port("port_middle_east"), Port("port_europe")]

    # legs: asia -> middle_east -> europe -> asia
    set_distance("port_asia", "port_middle_east", 5000)
    set_distance("port_middle_east", "port_europe", 6300)
    set_distance("port_europe", "port_asia", 10500)

    set_port_duration("*", "*", 1.5)
    set_port_duration("port_middle_east", "port_europe", 2.5)  # days in port_europe

    set_speed("*", "*", 16)
    set_utilization("*", "*", 0.8)
    set_utilization("port_europe", "port_asia", 0.6)
}
```

TRAMP example, with a distribution of speeds and ballast and laden sailing:

```python
Curve "bulk_speeds" {
    Table = [
        10.5  0.3
        11.5  0.4
        12.5  0.3
    ]
}

Curve "bulk_utilizations" {
    Table = [
        10.5  0.6
        11.5  0.5
        12.5  0.4
    ]
}

Route "bulk_global" {
    RouteType = TRAMP
    Ports = [Port("port_global"), Port("port_europe")]
    TimeAtSea = 0.65

    set_port_calls("port_global", 17)
    set_port_calls("port_europe", 3)

    set_voyage_distribution("*", "*", 1)
    set_voyage_distribution("port_europe", "port_europe", 0)

    set_speed("*", "*", Curve("bulk_speeds"))
    set_utilization("*", "*", Curve("bulk_utilizations"))
}
```

## Legs

A leg is the sailing from one port of the route to another. The route type decides which pairs of ports are legs:

* On a `LINER`, each port and the one after it in `Ports` form a leg, and the last port and the first form the closing leg. `Ports = [Port("a"), Port("b"), Port("c")]` gives the legs a → b, b → c and c → a.
* On a `TRAMP`, every ordered pair of ports is a leg, a port with itself included. `Ports = [Port("a"), Port("b")]` gives the legs a → a, a → b, b → a and b → b. A leg from a port to itself stands for sailing within that port's region.

The per-leg commands take the name of the leg's origin port, the name of its destination port, and the value. A port name may contain wildcards, but a wildcard only matches the route's existing legs: `set_speed("a", "*", 12)` sets every leg starting at `a`, and never creates a leg. A key that matches no leg, such as `set_speed("a", "c", 12)` on a `LINER` that sails a → b → c, is an error. Each command applies to the legs it matches in the order the commands are written, so a later command overrides an earlier one on the legs they share.

## Sailing conditions

A leg is sailed at one speed, or at a distribution of speeds given by a `Curve` in [set\_speed](#set_speed). Each speed of the distribution is a sailing condition of the leg, with its own share of the leg's time at sea and, on a `TRAMP`, its own cargo utilization from [set\_utilization](#set_utilization).

The number of sailing conditions on each leg is fixed when the `DEFINE` section is read. An `EVENTS` assignment may change the speeds and their shares, but not their number: replacing a single speed by a `Curve`, or a `Curve` by one with a different number of rows, is an error.

## Conditions

The following conditions apply to every route:

* Each per-leg input is set for the route's legs only; see [Legs](#legs).
* A required per-leg input left unset on any leg is an error naming the legs.
* A command or attribute that does not apply to the route type is an error.

If RouteType is LINER:

* A minimum of 2 ports must be assigned.
* A port cannot be placed directly after itself, and the same port cannot be placed both first and last, because the list of ports wraps around.
* A port may be called more than once, but each leg may only be sailed once: `[Port("a"), Port("b"), Port("a"), Port("c")]` is accepted, `[Port("a"), Port("b"), Port("a"), Port("b")]` is not.
* [set\_speed](#set_speed), [set\_distance](#set_distance) and [set\_port\_duration](#set_port_duration) must be given for every leg.
* [TimeAtSea](#timeatsea), [set\_voyage\_distribution](#set_voyage_distribution), [set\_port\_calls](#set_port_calls) and a `Curve` in [set\_utilization](#set_utilization) do not apply.

If RouteType is TRAMP:

* All ports must be unique.
* [TimeAtSea](#timeatsea) must be provided, and [set\_speed](#set_speed) and [set\_voyage\_distribution](#set_voyage_distribution) must be given for every leg.
* [set\_distance](#set_distance) and [set\_port\_duration](#set_port_duration) do not apply.

## Attributes

### RouteType

This attribute sets the route type, `LINER` or `TRAMP`, which decides the legs of the route (see [Legs](#legs)) and which inputs it reads (see [Conditions](#conditions)).

A `LINER` describes one voyage around its ports in the listed order. Each leg is given its distance, its speed and its cargo utilization, and the time in port at the end of it. The time at sea follows from the distances and speeds.

A `TRAMP` describes a year of operation between a pool of ports, with no start, end or order. [TimeAtSea](#timeatsea) sets the share of the year spent at sea, and the sea miles sailed in that time are split between the legs by [set\_voyage\_distribution](#set_voyage_distribution). The time in port is split between the ports by [set\_port\_calls](#set_port_calls).

The type describes the calculation, not the market segment: choose `LINER` where the route's distances and port times are known leg by leg, and `TRAMP` where the operation is known as shares of a year.

* **Data type**: `ID`
* **Legal values**: [RouteTypeID](appendix_ids.md#routetypeid)
* **Default**: None. Must be provided by the user.

### Ports

This attribute sets the list of ports the vessel calls at, and at which it may bunker. On a `LINER` the order of the list is the order of the calls; on a `TRAMP` the order does not matter. The rules on the number and order of ports depend on the RouteType; see [Conditions](#conditions). This is the only attribute that keeps a `Port` in the simulation — a port on no route is removed (see [Unreachable nodes](dsl_reference.md#unreachable-nodes)).

* **Data type**: List of `Port` nodes
* **Example values**:
  + `[Port("name")]`
  + `[Port("name1"), Port("name2"), Port("name3")]`
  + `[Port("*")]`
* **Default**: None. Must be provided by the user.

### TimeAtSea

This attribute sets the fraction of the year spent at sea; the rest of the year is spent in port. It only applies to a `TRAMP` route, and is an error on a `LINER`, whose time at sea follows from its distances and speeds.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.75`
  + `Forecast("name")`
* **Unit**: Fraction of time spent at sea per total time
* **Minimum value**: >0
* **Maximum value**: 1
* **Default**: None. Must be provided by the user when RouteType is TRAMP.

## Commands

### set\_speed

This command sets the speed sailed on a leg, in knots. It applies to both route types and must be given for every leg.

A number, `Variable` or expression gives the leg one speed. A `Curve` gives a distribution of speeds: its x-values are the speeds in knots, and its y-values the share of the leg's time at sea sailed at each speed. Each speed is a sailing condition of the leg (see [Sailing conditions](#sailing-conditions)). The shares are read through the Curve, so its `Addition`, `Multiplier` and bounds apply, and they must sum to 1, rounded to five decimals; they are not rescaled. An expression gives one speed and may not reference a `Curve`.

The speed is the reference speed of the leg; [speed management](fleet.md#allowspeedmanagement) on the Fleet may change it over the simulation.

* **Primary key type**: String (Port name of the leg's origin; supports wildcards)
* **Secondary key type**: String (Port name of the leg's destination; supports wildcards)
* **Data type**: `Float`, `Curve`, `Variable`
* **Example values**:
  + `"port_name_from", "port_name_to", 12`
  + `"*", "*", Curve("speed_distribution")`
  + `"port_name_from", "*", Variable("name")`
* **Unit**: Knots; for a `Curve`, x: Knots, y: Fraction of the leg's time at sea
* **Minimum value**: >0; for a `Curve`, x: >0, y: 0
* **Maximum value**: For a `Curve`, y: 1
* **Default**: None. Must be provided by the user for every leg.

### set\_utilization

This command sets the cargo capacity utilization on a leg. It applies to both route types.

A number, `Forecast`, `Variable` or expression gives the leg one utilization, which applies to every sailing condition of the leg. An expression may not reference a `Curve`.

On a `TRAMP`, a `Curve` gives a utilization per speed: its x-values must equal those of the leg's speed `Curve` in [set\_speed](#set_speed), and its y-values are the utilization at each speed. The utilization belongs to the sailing condition, so it does not change when speed management moves the condition's speed. This is how ballast and laden sailing are expressed: the utilization at a speed is the mean over the time sailed at that speed, so a vessel laden half of that time and in ballast the other half has a utilization of 0.5. A `Curve` is an error on a `LINER`, where each leg has its own utilization, and on a leg sailed at one speed.

* **Primary key type**: String (Port name of the leg's origin; supports wildcards)
* **Secondary key type**: String (Port name of the leg's destination; supports wildcards)
* **Data type**: `Float`, `Curve` (TRAMP only), `Forecast`, `Variable`
* **Example values**:
  + `"port_name_from", "port_name_to", 0.8`
  + `"*", "*", Curve("utilization_per_speed")`
  + `"port_name_from", "*", Forecast("name")`
* **Unit**: Fraction of cargo capacity; for a `Curve`, x: Knots, y: Fraction of cargo capacity
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 1 on every leg.

### set\_distance

This command sets the distance of a leg, in nautical miles. It only applies to a `LINER` route, where it must be given for every leg, and is an error on a `TRAMP`.

This command is only allowed in the `DEFINE` section.

* **Primary key type**: String (Port name of the leg's origin; supports wildcards)
* **Secondary key type**: String (Port name of the leg's destination; supports wildcards)
* **Data type**: `Float`
* **Example values**:
  + `"port_name_from", "port_name_to", 1470`
  + `"port_name_from", "port_name_to", <2 * 735>`
* **Unit**: Nautical miles
* **Minimum value**: >0
* **Default**: None. Must be provided by the user for every leg of a LINER.

### set\_port\_duration

This command sets the time spent in port at the end of a leg, in days: the time at the leg's destination port before the next leg starts. A port called more than once on a `LINER` has a duration for each call, set on the leg that arrives at it. The command only applies to a `LINER` route, where it must be given for every leg, and is an error on a `TRAMP`.

* **Primary key type**: String (Port name of the leg's origin; supports wildcards)
* **Secondary key type**: String (Port name of the leg's destination; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"port_name_from", "port_name_to", 3.5`
  + `"*", "*", Forecast("name")`
* **Unit**: Days
* **Minimum value**: 0
* **Default**: None. Must be provided by the user for every leg of a LINER.

### set\_voyage\_distribution

This command sets the share of the sea miles sailed on a leg. It only applies to a `TRAMP` route, where it must be given for every leg, and is an error on a `LINER`. A share of 0 is allowed and means the leg is not sailed.

The shares are rescaled to sum to 1 over the legs; if they are all 0, every leg gets an equal share. `set_voyage_distribution("*", "*", 1)` therefore gives every leg the same share.

* **Primary key type**: String (Port name of the leg's origin; supports wildcards)
* **Secondary key type**: String (Port name of the leg's destination; supports wildcards)
* **Data type**: `Float`, `Variable`
* **Example values**:
  + `"port_name_from", "port_name_to", 0.5`
  + `"*", "*", 1`
  + `"port_name_from", "port_name_to", Variable("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: None. Must be provided by the user for every leg of a TRAMP.

### set\_port\_calls

This command sets the number of calls at a port over the year a `TRAMP` route describes. The time in port is split between the ports in proportion to their calls. It only applies to a `TRAMP` route, and is an error on a `LINER`. A port name that matches none of the route's `Ports` is an error.

* **Primary key type**: String (Port name; supports wildcards)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"port_name", 20`
  + `"*", Forecast("name")`
* **Unit**: Number of port calls per year
* **Minimum value**: >0
* **Default**: 1 for every port.
