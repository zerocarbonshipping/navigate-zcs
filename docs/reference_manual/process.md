<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Process

A `Process` node defines a fuel production process used to build the bottom-up fuel production hierarchy.
Processes explains the conversion of feedstock and other intermediate processes into a new output stream. 
Examples of processes are Haber-Bosch and methane liquefaction.

Example:

```python
Process "haber_bosch_electro" {
	Feeds = [Process("hydrogen_compression_electro"), Process("nitrogen_air_separation")]
	Conversions = [0.18, 0.822]
}
```


## Attributes

### Feeds

This attribute defines a list of feeds used in the production process of a fuel. In this terminology a feeds can also be a Process node in which case it is interpreted as the output from that process.

The number of Feeds and the number of Conversions must correspond.

All 'Feeds' must be unique, i.e., a feedstock cannot be duplicated in the input list.

* **Data type**: List of `Feedstock`, `Process` nodes
* **Example values**:
  + `[Feedstock("name")]`
  + `[Feedstock("name"), Process("name")]`
* **Default**: None

### Conversions

This attribute specifies a list of conversion factors. A conversion factor describes how many tons of feed are needed to produce one ton of fuel. The number of Feeds and the number of Conversions must correspond.

* **Data type**: List of `Floats`, `Forecast`, `Variables`
* **Example values**:
  + `[0.5, 2.5]`
  + `[Forecast("name"), Variable("name")]`
* **Unit**: ton feeds / ton output
* **Minimum value**: 0
* **Default**: None
