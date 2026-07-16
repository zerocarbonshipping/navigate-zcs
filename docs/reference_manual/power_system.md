<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# PowerSystem

A `PowerSystem` node defines a collection of converters which make up the full power system used to satisfy
the propulsion, electrical, and heat demand of a vessel. Examples of power systems are a conventional
main engine, auxiliary engine, and boiler and a diesel-electric setup.

Example:

```python
PowerSystem "conventional" {
    Propulsion = Converter("main_engine")
    Electrical = Converter("auxiliary_engine")
    Heat = Converter("boiler")
    
    CAPEX = 1e6
    OPEX = 1e4
}
```

## Attributes

### CAPEX

This attribute represents the CAPEX (capital expenditure) for installing the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1e6`
  + `Forecast("name")`
* **Unit**: USD
* **Minimum value**: 0
* **Default**: 0

### OPEX

This attribute represents the OPEX (operational expenditure) for maintaining the machinery annually.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1e4`
  + `Forecast("name")`
* **Unit**: USD/year
* **Minimum value**: 0
* **Default**: 0

### Lifetime

This attribute sets the lifetime of the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `25`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: Vessel lifetime.

### Replacement

This attribute sets the fraction of CAPEX paid when part of the machinery is replaced at the end of the part’s lifetime.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.5`
  + `Forecast("name")`
* **Unit**: Fraction
* **Minimum value**: 0
* **Default**: 1

### Propulsion \*

This attribute defines the converter used to satisfy the propulsion demand.

* **Data type**: `Converter`
* **Example values**:
  + `Converter("name")`
* **Default**: None. Must be provided by the user.

### Electrical \*

This attribute defines the converter used to satisfy the electrical demand.

* **Data type**: `Converter`
* **Example values**:
  + `Converter("name")`

### Heat \*

This attribute defines the converter used to satisfy the heat demand.

* **Data type**: `Converter`
* **Example values**:
  + `Converter("name")`
