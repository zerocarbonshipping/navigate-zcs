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
* **Format**: dd-mm-yyyy, separated by hyphens or slashes
* **Example values**:
  + `"01-01-2024"`
  + `"01/01/2024"`
* **Default**: None. Must be provided by the user.

### EmissionsLifetime

This attribute determines the emission lifetime used to calculate the Global Warming Potential (GWP) value for the computation of CO<sub>2</sub> equivalent emissions.

* **Data type**: `Float`
* **Example value**: `20`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 100

### Currency

This attribute names the currency of every monetary input and result. Navigate converts no currency, so every monetary input of the deck must be in it, those it loads from the assumptions library included, which are in USD. The reference manual writes a monetary unit with `currency`, such as `currency/ton` for a bunker price, and the [results file](results_file.md#metadata) writes the currency in its place, such as `EUR/t`.

* **Data type**: `String`, one word without a slash
* **Example values**:
  + `"USD"`
  + `"EUR"`
* **Default**: `"USD"`
