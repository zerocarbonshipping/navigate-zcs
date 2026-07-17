<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Surface

A `Surface` node defines a three-dimensional relation between x-, y-, and z-values. Several attributes of other
nodes allows the assignment of a surfaces. An example is the assignment of a speed-draft-power surface which
takes the speed as an x-value, the draft (cargo-utilization) as a y-value and returns the required power as
a z-value.

Calculations in surfaces are done using the following formula:

$$
z = \min\left(\max\left(\text{Multiplier} \cdot (z(x, y) + \text{Addition}), \text{LowerBound}\right), \text{UpperBound}\right)
$$

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

### Addition

Sets an addition that is added on the z-values. The addition occurs according to the formula


* **Data type**: `Float`
* Example value: `10`
* **Default**: 0

### Multiplier

Sets a multiplier that is multiplied to the z-values. The multiplication occurs according to the formula


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
* **Legal values**: [Interpolate2DID](appendix_ids.md#interpolate2did)
* **Default**: LINEAR

### Extrapolate

This attribute sets the extrapolation method used extrapolate outside the table.

* **Data type**: `ID`
* **Legal values**: [ExtrapolateID](appendix_ids.md#extrapolateid)
* **Default**: LINEAR

### Outside 

This attribute sets the flat extrapolation value outside the table. This value must be defined if ‘Extrapolate’ is set to FLAT.

* **Data type**: `Float`
* Example value: `20`
* **Default**: None
