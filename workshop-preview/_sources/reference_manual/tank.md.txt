<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Tank

A `Tank` node defines a tank onboard a vessel used for storage of fuel. Examples of tanks are the conventional
tanks for storage of heavy fuel oil and cylindrical tanks for storing liquefied gas.

Example:

```python
Tank "fuel_oil_tank" {
    FuelTypes = [OIL]
    Size = 5000
    
    CAPEX = 500
    OPEX = 5
}
```

## Attributes

### CAPEX

This attribute represents the CAPEX (capital expenditure) for installing the machinery.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `1000`
  + `Forecast("name")`
* **Unit**: USD/m<sup>3</sup>
* **Minimum value**: 0
* **Default**: 0

### OPEX

This attribute represents the OPEX (operational expenditure) for maintaining the machinery annually.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `10`
  + `Forecast("name")`
* **Unit**: USD/m<sup>3</sup>/year
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

### FuelTypes 

This attribute sets the types of fuel that can be stored in the tank. At least one fuel type must be assigned.

* **Data type**: List of `IDs`
* **Legal values**: [FuelTypeID](appendix_ids.md#fueltypeid)
* **Example values**:
  + `OIL`
  + `[OIL, METHANOL]`
* **Default**: None. Must be provided by the user.

### Size 

This attribute sets the volumetric size of the tank in cubic meters.

* **Data type**: `Float`
* Example value: `8000`
* **Unit**: Cubic Meter (m3)
* **Minimum value**: 0
* **Default**: None. Must be provided by the user.
