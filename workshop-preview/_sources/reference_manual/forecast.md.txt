<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Forecast

A `forecast` node defines a two-dimensional relation between t- and y-values where the t-values are dates.
Several attributes of other nodes allows the assignment of a forecast. An example is the assignment of the
expected increase in plant capacity over time which return the expected plant capacity as a y-value for
a given time-step in the simulation.

Calculations in forecasts are done using the following formula:

$$
y = \min\left(\max\left(\text{Multiplier} \cdot (y(t) + \text{Addition}), \text{LowerBound}\right), \text{UpperBound}\right)
$$

Example:

```python
Forecast "methanol_plant_capacity" {
    Table = [
        "01-01-2025" 160
        "01-01-2030" 320
        "01-01-2035" 640
        "01-01-2045" 3200
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
