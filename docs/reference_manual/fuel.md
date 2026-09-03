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
* **Default**: None. Must be defined by the user.

### LiquidMarket

This attribute specifies whether the fuel belongs to a liquid market. Fuels which belong to a liquid market cannot be modelled bottom-up via `Plant` and `Producer` nodes but require manual assignment of supply, price, and WTT emissions at `Port` level (see `set_bunker_price_overwrite` and `set_bunker_wtt_overwrite` on the [Port](port.md) node).

* **Data type**: `Bool`
* **Example values**: `TRUE`
* **Default**: `FALSE`

### LowerHeatingValue

This attribute sets the lower heating value of the fuel in GJ/ton.

* **Data type**: `Float`, `Variable`
* **Example values**: `42.6`
* **Unit**: GJ/ton
* **Minimum value**: >0
* **Default**: None

### MassDensity

This attribute describes the mass density of the fuel.

* **Data type**: `Float`, `Variable`
* **Example values**: `0.96`
* **Unit**: ton/m<sup>3</sup>
* **Minimum value**: >0
* **Default**: None

## Commands

### set\_ttw

This command allows the user to set the tank-to-wake (TTW) emission factor.

* **Primary key type**: String (Emission name)
* **Data type**: `Float`, `Variable`
* **Example values**:
  + `"emission_name", 2.75`
  + `"emission_name", Variable("name")`
* **Unit**: ton emission / ton fuel
* **Default**: 0
