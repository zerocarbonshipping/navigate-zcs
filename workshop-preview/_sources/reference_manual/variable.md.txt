<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Variable

A `Variable` node defines a single value that can be used across multiple attributes. Examples of variables
are physical properties such as mass densities lower heating values.

Calculations in variables are done using the following formula:

$$
y = \min\left( \max\left( \text{Multiplier} \cdot (\text{Value} + \text{Addition}), \text{LowerBound} \right), \text{UpperBound} \right)
$$

Example:

```python
Variable "lower_heating_value_diesel" {
    Value = 42.7
}
```

## Attributes

### Value

Sets the value of the variable.

* **Data type**: `Float`
* Example value: `42.7`
* **Default**: None. Must be provided by the user.

### Addition

Sets an addition that is added on the value. The addition occurs according to the formula

* **Data type**: `Float`
* Example value: `10`
* **Default**: 0

### Multiplier

Sets a multiplier that is multiplied to the value. The multiplication occurs according to the formula

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
