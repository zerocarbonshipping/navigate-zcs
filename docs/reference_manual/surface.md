<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Surface

A `Surface` node defines a three-dimensional relation between x-, y-, and z-values. Several attributes of other
nodes allow the assignment of a surface. An example is the assignment of a speed-draft-power surface which
takes the speed as an x-value, the draft (cargo-utilization) as a y-value and returns the required power as
a z-value.

Calculations in surfaces are done using the following formula, where $z(x, y)$ is the value looked up in the table:

$$
z = \min\left(\max\left(\text{Multiplier} \cdot (z(x, y) + \text{Addition}), \text{LowerBound}\right), \text{UpperBound}\right)
$$

The `Addition` is applied before the `Multiplier`, and the bounds are applied last.

An attribute that references the node holds $z$ to its own minimum and maximum value as well: an inclusive one clamps $z$, and $z$ reaching an exclusive one stops the run with an error. See [Assigning attributes](dsl_reference.md#assigning-attributes).

Example:

```python
Surface "speed_power_draft_surface" {
    Table = [
        # first row is y-axis
        # first column is x-axis
           0.0 1.0  # CargoUtilization (0-1) is used as a proxy for draft
        9  3.2 4.1
        10 4.4 5.8
        11 5.9 7.8
        12 7.7 10.1
        13 9.8 13.2
        14 12.6 16.6
        15 15.7 19.1
    ]
    
    Extrapolate = FLAT
}
```

## Attributes

### Table

This attribute sets the table of x-, y- and z-values that the surface interpolates in. There must be at least two x-values and two y-values, each finite and strictly increasing, and the number of z-values must equal the number of x-values times the number of y-values. A z-value may be `INF` or `-INF`, but not `nan`. The syntax is described under [Assigning tables](dsl_reference.md#surface).

* **Data type**: `Table`
* **Default**: None. Must be provided by the user.

### Addition

Sets a value that is added to the z-value looked up in the table, before the `Multiplier` is applied, according to the [formula](#surface) at the top of this page. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are rejected.

* **Data type**: `Float`, `Expression`
* **Example value**: `10`
* **Default**: 0

### Multiplier

Sets a factor that the z-value looked up in the table, plus the `Addition`, is multiplied by, according to the [formula](#surface) at the top of this page. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are rejected.

* **Data type**: `Float`, `Expression`
* **Example value**: `2.5`
* **Default**: 1

### LowerBound

Sets the lower bound that the result is clamped to after the `Addition` and the `Multiplier` are applied, according to the [formula](#surface) at the top of this page. `-INF` means no lower bound; `INF` is rejected.

* **Data type**: `Float`
* **Example value**: `-5`
* **Default**: -INF

### UpperBound

Sets the upper bound that the result is clamped to after the `Addition` and the `Multiplier` are applied, according to the [formula](#surface) at the top of this page. `INF` means no upper bound; `-INF` is rejected.

* **Data type**: `Float`
* **Example value**: `5`
* **Default**: INF

### Interpolate

This attribute sets the interpolation method used to interpolate in the table.

* **Data type**: `ID`
* **Legal values**: [Interpolate2DID](appendix_ids.md#interpolate2did)
* **Default**: LINEAR

### Extrapolate

This attribute sets the extrapolation method used to extrapolate outside the table. With `FLAT`, the value of `Outside` is used.

* **Data type**: `ID`
* **Legal values**: [ExtrapolateID](appendix_ids.md#extrapolateid)
* **Default**: LINEAR

### Outside 

This attribute sets the flat extrapolation value outside the table. It is only used when `Extrapolate` is `FLAT`, and it then takes the place of the table's z-value in the [formula](#surface) at the top of this page; when `Extrapolate` is not `FLAT`, a value set here is ignored with a warning. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are accepted, and are checked against each attribute the surface is assigned to (see [Assigning attributes](dsl_reference.md#assigning-attributes)).

* **Data type**: `Float`, `Expression`
* **Example value**: `20`
* **Default**: None. Must be provided by the user when `Extrapolate` is `FLAT`.
