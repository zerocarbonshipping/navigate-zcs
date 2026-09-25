<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# ModelDefinition

The `ModelDefinition` general node defines system-wide information about the simulation.

Example:

```python
ModelDefinition {
    StartDate = "01-01-2024"
    EmissionsLifetime = 100
}
```


## Attributes

### StartDate

This attribute sets the start date of the simulation.

* **Data type**: `date`
* **Example values**:
  + `"01-01-2024"`
  + `"01/01/2024"`
* **Default**: None. Must be provided by the user.

### EmissionsLifetime

This attribute determines the emission lifetime used to calculate the Global Warming Potential (GWP) value for the computation of CO<sub>2</sub> equivalent emissions.

* **Data type**: `Float`
* Example value: `20`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 100
