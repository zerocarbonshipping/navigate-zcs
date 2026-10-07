<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Fuel

A `Fuel` node defines a fuel which can be used as a bunker fuel onboard a vessel. Examples of fuels are
liquefied natural gas and e-ammonia.

Example:

```python
Fuel "liquefied_natural_gas" {
	FuelType = METHANE
	LiquidMarket = TRUE
	
	LowerHeatingValue = Variable("lower_heating_value_natural_gas")
	MassDensity = Variable("mass_density_liquefied_natural_gas")
	
	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_natural_gas"))
}
```

## Attributes

### FuelType 

This attribute specifies the type of the fuel.

* **Data type**: `ID`
* **Legal values**: [FuelTypeID](appendix_ids.md#fueltypeid)
* **Default**: None. Must be provided by the user.

### LiquidMarket

This attribute specifies whether the fuel belongs to a liquid market. Fuels which belong to a liquid market cannot be modelled bottom-up via `Plant` and `Producer` nodes but require manual assignment of supply, price, and WTT emissions at `Port` level (see `set_bunker_price_overwrite` and `set_bunker_wtt_overwrite` on the [Port](port.md) node).

* **Data type**: `Boolean`
* **Example value**: `TRUE`
* **Default**: FALSE

### LowerHeatingValue

This attribute sets the lower heating value of the fuel in GJ/ton.

* **Data type**: `Float`, `Variable`
* **Example values**:
  + `42.6`
  + `Variable("name")`
* **Unit**: GJ/ton
* **Minimum value**: >0
* **Default**: None. Must be provided by the user.

### MassDensity

This attribute sets the mass density of the fuel in ton/m<sup>3</sup>.

* **Data type**: `Float`, `Variable`
* **Example values**:
  + `0.96`
  + `Variable("name")`
* **Unit**: ton/m<sup>3</sup>
* **Minimum value**: >0
* **Default**: None. Must be provided by the user.

## Commands

### set\_ttw

This command sets the tank-to-wake (TTW) emission factor of the fuel for an emission, from the stoichiometric conversion of the fuel to energy.

This command is only allowed in the `DEFINE` section.

* **Primary key type**: String (Emission name; supports wildcards)
* **Data type**: `Float`, `Variable`
* **Example values**:
  + `"emission_name", 2.75`
  + `"emission_name", Variable("name")`
* **Unit**: ton emission / ton fuel
* **Minimum value**: 0
* **Default**: 0
