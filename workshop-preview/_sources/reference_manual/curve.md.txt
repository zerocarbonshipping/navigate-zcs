<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Curve

A `Curve` node defines a two-dimensional relation between x- and y-values. Several attributes of other nodes
allows the assignment of a curve. An example is the assignment of a speed-power curve which takes the speed
as an x-value and returns the required power as a y-value.

Calculations in curves are done using the following formula:

$$
y = \min\left(\max\left(\text{Multiplier} \cdot (y(x) + \text{Addition}), \text{LowerBound}\right), \text{UpperBound}\right)
$$

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

### Addition

Sets an addition that is added on the y-values. The addition occurs according to the formula


* **Data type**: `Float`
* Example value: `10`
* **Default**: 0

### Multiplier

Sets a multiplier that is multiplied to the y-values. The multiplication occurs according to the formula


* **Data type**: `Float`
* Example value: `2.5`
* **Default**: 1

### LowerBound

Sets the lower bound. The lower bound is used according to the formula:


* **Data type**: `Float`
* Example value: `-5`
* **Default**: -INF

### UpperBound

Sets the upper bound. The upper bound is used according to the formula:


* **Data type**: `Float`
* Example value: `5`
* **Default**: INF

### Interpolate

This attribute sets the interpolation method used to interpolate in the table.

* **Data type**: `ID`
* **Legal values**: [Interpolate1DID](appendix_ids.md#interpolate1did)
* **Default**: LINEAR

### Extrapolate

This attribute sets the extrapolation method used extrapolate outside the table.

* **Data type**: `ID`
* **Legal values**: [ExtrapolateID](appendix_ids.md#extrapolateid)
* **Default**: LINEAR

### Below

Sets the flat extrapolation value below the table. If no value is defined and the extrapolation is set to flat the first y-value in the table is used:

* **Data type**: `Float`
* Example value: `-5`
* **Default**: None

### Above

Sets the flat extrapolation value above the table. If no value is defined and the extrapolation is set to flat the last y-value in the table is used:

* **Data type**: `Float`
* Example value: `5`
* **Default**: None
