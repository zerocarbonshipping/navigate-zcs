<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Source

A `Source` node defines a source of energy for fuel production. Examples of sources are the grid and stand-alone
renewable electricity generation.

Example:

```python
Source "grid" {
    Dependency = CONNECTED
}
```

## Attributes

### Dependency

This attribute sets dependency of the source. Namely whether it has stand-alone energy production or is connected to an external source such as a countries power grid.

* **Data type**: `ID`
* **Legal values**: [SourceDependencyID](appendix_ids.md#sourcedependencyid)
* **Default**: CONNECTED
