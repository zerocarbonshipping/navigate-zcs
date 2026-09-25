<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Timetable

A `Timetable` node defines a three-dimensional relation between t-, y-, and z-values. Where the t-values are
dates. Several attributes of other nodes allows the assignment of a timetable. An example is the assignment
of the CAPEX of a fuel production process which takes the date as a t-value, the plant capacity as a y-value
and returns the capital expenditure as a z-value.

Calculations in timetables are done using the following formula:

$$
z = \min\left( \max\left( \text{Multiplier} \cdot (z(t, y) + \text{Addition}), \text{LowerBound} \right), \text{UpperBound} \right)
$$

Example:

```python
Timetable "methanol_synthesis_capex" {
    Table = [
                     160 320 640 3200
        "01-01-2025" 2700 2000 1500 1000
        "01-01-2030" 2500 1700 1200 800
    ]
    
    Extrapolate = LINEAR
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
