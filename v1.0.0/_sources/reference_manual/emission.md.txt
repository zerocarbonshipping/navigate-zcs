<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Emission

An `Emission` node defines an emission that will be tracked by the simulation.
Examples of emissions are carbon dioxide, methane, nitrous oxide, NOx, and SOx.

Example:

```python
Emission "methane" {
    GlobalWarmingPotential = Curve("GWP_methane")
}
```

## Attributes

### GlobalWarmingPotential

This attribute specifies the Global Warming Potential (GWP) of the emission. The global warming potential indicates the level of radiative forcing (i.e., warming) that is expected of a certain emission over time. It thereby allows for comparison across different types of emissions, e.g., carbon dioxide and methane.

* **Data type**: `Float`, `Curve`, `Variable`
* **Example Values**:
  + 36.6
  + Curve("name")
* **Unit**: ton CO<sub>2</sub> equivalent / ton emission
* **Minimum value**: 0
* **Default**: 0
