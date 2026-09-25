<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Feedstock

A `Feedstock` node defines a feedstock used in the production of fuels. Examples of feedstocks are
natural gas and biomass.

Example:

```python
Feedstock "natural_gas" {}
```

A `Feedstock` node has no attributes or commands. It only defines the feedstock by name so that other
nodes can refer to it. Feedstock-related values are set on the nodes that use the feedstock:

* [Region](region.md): `set_feedstock_cost` and `set_feedstock_wtt` set the cost and WTT emissions of the feedstock in a region.
* [Plant](plant.md): `set_feed_transport` and `set_feed_distance` set how the feedstock is transported to the plant and over what distance.
* [Producer](producer.md): `set_feed_constraint` limits the amount of the feedstock available in a region in tons/year.
