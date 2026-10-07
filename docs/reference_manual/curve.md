<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Curve

A `Curve` node defines a two-dimensional relation between x- and y-values. Several attributes of other nodes
allow the assignment of a curve. An example is the assignment of a speed-power curve which takes the speed
as an x-value and returns the required power as a y-value.

Calculations in curves are done using the following formula, where $y(x)$ is the value looked up in the table:

$$
y = \min\left(\max\left(\text{Multiplier} \cdot (y(x) + \text{Addition}), \text{LowerBound}\right), \text{UpperBound}\right)
$$

The `Addition` is applied before the `Multiplier`, and the bounds are applied last.

An attribute that references the node holds $y$ to its own minimum and maximum value as well: an inclusive one clamps $y$, and $y$ reaching an exclusive one stops the run with an error. See [Assigning attributes](dsl_reference.md#assigning-attributes).

Example:

```python
Curve "speed_power_curve" {
	Table = [
		10	3.4
		11	4.8
		12	7.2
		13	9.2
		14	11.2
		15	13.9
		16	17.1
		17	20.5
		18	24.5
		19	28.9
		20	33.9
		21	39.9
		22	46.7
		23	54.5
	]
    
	Extrapolate = LINEAR
}
```


## Attributes

### Table

This attribute sets the table of x- and y-values that the curve interpolates in. The table must hold at least two rows and its x-values must be finite and strictly increasing. A y-value may be `INF` or `-INF`, but not `nan`. The syntax is described under [Assigning tables](dsl_reference.md#curve).

* **Data type**: `Table`
* **Default**: None. Must be provided by the user.

### Addition

Sets a value that is added to the y-value looked up in the table, before the `Multiplier` is applied, according to the [formula](#curve) at the top of this page. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are rejected.

* **Data type**: `Float`, `Expression`
* **Example value**: `10`
* **Default**: 0

### Multiplier

Sets a factor that the y-value looked up in the table, plus the `Addition`, is multiplied by, according to the [formula](#curve) at the top of this page. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are rejected.

* **Data type**: `Float`, `Expression`
* **Example value**: `2.5`
* **Default**: 1

### LowerBound

Sets the lower bound that the result is clamped to after the `Addition` and the `Multiplier` are applied, according to the [formula](#curve) at the top of this page. `-INF` means no lower bound; `INF` is rejected.

* **Data type**: `Float`
* **Example value**: `-5`
* **Default**: -INF

### UpperBound

Sets the upper bound that the result is clamped to after the `Addition` and the `Multiplier` are applied, according to the [formula](#curve) at the top of this page. `INF` means no upper bound; `-INF` is rejected.

* **Data type**: `Float`
* **Example value**: `5`
* **Default**: INF

### Interpolate

This attribute sets the interpolation method used to interpolate in the table. `PREVIOUS` and `NEXT` cannot be combined with `Extrapolate = LINEAR`; such a curve is rejected.

* **Data type**: `ID`
* **Legal values**: [Interpolate1DID](appendix_ids.md#interpolate1did)
* **Default**: LINEAR

### Extrapolate

This attribute sets the extrapolation method used to extrapolate outside the table. With `FLAT`, the values of `Below` and `Above` are used.

* **Data type**: `ID`
* **Legal values**: [ExtrapolateID](appendix_ids.md#extrapolateid)
* **Default**: LINEAR

### Below

Sets the flat extrapolation value below the first x-value of the table. It is only used when `Extrapolate` is `FLAT`, and it then takes the place of the table's y-value in the [formula](#curve) at the top of this page. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are accepted, and are checked against each attribute the curve is assigned to (see [Assigning attributes](dsl_reference.md#assigning-attributes)).

* **Data type**: `Float`, `Expression`
* **Example value**: `-5`
* **Default**: Not set. The first y-value in the table is used.

### Above

Sets the flat extrapolation value above the last x-value of the table. It is only used when `Extrapolate` is `FLAT`, and it then takes the place of the table's y-value in the [formula](#curve) at the top of this page. The value may be an [expression](dsl_reference.md#expressions) of numbers; an expression that references a node is rejected. `INF` and `-INF` are accepted, and are checked against each attribute the curve is assigned to (see [Assigning attributes](dsl_reference.md#assigning-attributes)).

* **Data type**: `Float`, `Expression`
* **Example value**: `5`
* **Default**: Not set. The last y-value in the table is used.
