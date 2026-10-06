<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Vessel

A `Vessel` node defines a representative vessel which makes up part of the fleet. Examples of vessels
are a mono-fuel capesize bulk carrier and a dual-fuel methanol handy-max tanker.

Example:

```python
Vessel "bulk_carrier_capesize_oil" {

	PropulsionLoad = Surface("speed_draft_power_surface")
	ElectricalLoadAtSea = 0.7
	ElectricalLoadInPort = 0.7
	HeatLoadAtSea = 0.
	HeatLoadInPort = 0.9

	PowerSystem = PowerSystem("conventional_power_system")
	Tanks = [Tank("fuel_oil")]
	
	Route = Route("rotterdam_singapore")
	
	NominalCapacity = 200000
	
	Lifetime = 25
	CostOfCapital = Variable("cost_of_capital_vessel")
	Capex = 50e6
	Opex = 2.4e6
}
```

## Attributes

### PropulsionLoad

This attribute sets the propulsion load level in MW. This is the power required to propel the vessel (at a given speed and draft potentially). The cargo utilization is used as a proxy for a vessel’s draft, i.e., high cargo utilization is indicative of a higher draft. If a float is assigned the load level is independent of speed and draft, if a Curve is assigned the load level is only a function of speed and if a Surface is assigned it is both a function of speed and draft.

An expression assigned to this attribute is evaluated for the load, but it sets no technical speed limit and counts as non-convex, so the vessel's speed optimization logs a warning.

* **Data type**: `Float`, `Curve`, `Surface`, `Variable`
* **Example values**:
  + `16.5`
  + `Curve("name")`
  + `Surface("name")`
* **Unit**: MW
* **Unit x**: Knots (Curve and Surface)
* **Unit y**: MW (Curve); Fraction of cargo capacity (Surface)
* **Unit z**: MW (Surface)
* **Minimum value**: 0
* **Default**: 0

### ElectricalLoadAtSea

This attribute defines the electrical load level at sea in MW. This is the power required to run auxiliary systems on the vessel at sea at a given speed and cargo utilization. If a float is assigned the load level is independent of speed and draft, if a Curve is assigned the load level is only a function of speed and if a Surface is assigned it is both a function of speed and draft.

An expression assigned to this attribute is evaluated for the load, but it sets no technical speed limit and counts as non-convex, so the vessel's speed optimization logs a warning.

* **Data type**: `Float`, `Curve`, `Surface`, `Variable`
* **Example values**:
  + `16.5`
  + `Curve("name")`
  + `Surface("name")`
* **Unit**: MW
* **Unit x**: Knots (Curve and Surface)
* **Unit y**: MW (Curve); Fraction of cargo capacity (Surface)
* **Unit z**: MW (Surface)
* **Minimum value**: 0
* **Default**: 0

### ElectricalLoadInPort

This attribute sets the electrical load level in port in MW. This is the power required to run auxiliary systems on the vessel in port. Per definition, the load levels in port cannot depend on speed/draft as the vessel is not moving in port.

* **Data type**: `Float`, `Variable`
* **Example value**: `16.5`
* **Unit**: MW
* **Minimum value**: 0
* **Default**: 0

### HeatLoadAtSea

This attribute defines the heat load level at sea in MW. This is the power required to produce heat on the vessel at sea at a given speed and cargo utilization. If a float is assigned the load level is independent of speed and draft, if a Curve is assigned the load level is only a function of speed and if a Surface is assigned it is both a function of speed and draft.

An expression assigned to this attribute is evaluated for the load, but it sets no technical speed limit and counts as non-convex, so the vessel's speed optimization logs a warning.

* **Data type**: `Float`, `Curve`, `Surface`, `Variable`
* **Example values**:
  + `16.5`
  + `Curve("name")`
  + `Surface("name")`
* **Unit**: MW
* **Unit x**: Knots (Curve and Surface)
* **Unit y**: MW (Curve); Fraction of cargo capacity (Surface)
* **Unit z**: MW (Surface)
* **Minimum value**: 0
* **Default**: 0

### HeatLoadInPort

This attribute sets the heat load level in port in MW. This is the power required to produce heat on the vessel in port. Per definition, the load levels in port cannot depend on speed/draft as the vessel is not moving in port.

* **Data type**: `Float`, `Variable`
* **Example value**: `16.5`
* **Unit**: MW
* **Minimum value**: 0
* **Default**: 0

### FuelType

This attribute sets the main fuel type of the vessel.

* **Data type**: `ID`
* **Legal values**: [FuelTypeID](appendix_ids.md#fueltypeid)
* **Default**: Not set. The main fuel type with the largest power capacity summed over the converters in the power system is used. A tie between fuel types is broken by the size of the tanks that store them.

### PowerSystem 

This attribute specifies the PowerSystem that is used to convert fuel to energy.

* **Data type**: `PowerSystem` node
* **Example value**: `PowerSystem("name")`
* **Default**: None. Must be provided by the user.

### Tanks 

This attribute sets the list of tanks used for onboard fuel storage. All Tanks assigned must be unique, i.e., they cannot be duplicated in the input list.

The list of tanks must include, for each converter in the PowerSystem, at least one tank that stores one of the converter's MainFuelTypes; for a dual-fuel converter with a MinimumPilotFuel above 0, one of its PilotFuelTypes instead.

* **Data type**: List of `Tank` nodes
* **Example values**:
  + `[Tank("name")]`
  + `[Tank("name1"), Tank("name2")]`
  + `[Tank("*")]`
* **Default**: None. Must be provided by the user.

### Route 

This attribute defines the route the vessel is sailing on.

* **Data type**: `Route` node
* **Example value**: `Route("name")`
* **Default**: None. Must be provided by the user.

### NominalCapacity 

This attribute sets the nominal cargo capacity of the vessel. This describes how much cargo the vessel is designed to be able to carry (while the amount of cargo actually being carried might be lower). The unit is not strictly defined but should match the 'Trade' attribute of the Fleet node that the vessel is assigned to. In general, the most logical unit for the vessel segment is applied, such as TEU for Container, CEU for RoRo, and dwt for Bulk Carrier.

* **Data type**: `Float`, `Variable`
* **Example values**:
  + `8000`
  + `Variable("name")`
* **Unit**: Varies depending on vessel type (e.g., TEU, CEU, dwt)
* **Minimum value**: 0
* **Default**: None. Must be provided by the user.

### Lifetime

This attribute defines the lifetime of the vessel in years. The vessel is scrapped when it surpasses its lifetime.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `25`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: >0
* **Default**: 25

### LeadTime

This attribute defines the lead time of the vessel in years. The lead time is only used for the calculation of the levelized cost of a vessel (charter rate) and does not impact the delivery of vessels.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `2`
  + `Forecast("name")`
* **Unit**: Years
* **Minimum value**: 0
* **Default**: 0

### Capex

This attribute sets the base CAPEX of building the vessel in USD.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `100e6`
  + `Forecast("name")`
* **Unit**: USD
* **Minimum value**: 0
* **Default**: 0

### Opex

This attribute defines the base OPEX of maintaining the vessel, in USD per year.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `10e6`
  + `Forecast("name")`
* **Unit**: USD per year
* **Minimum value**: 0
* **Default**: 0

### CostOfCapital

This attribute sets the cost of capital used to calculate the costs associated with financing the investment (through debt and equity). It is the discount rate used in calculating the levelized cost of cargo moved (the charter rate), and in the vessel's technology investment and fuel conversion decisions. The fleet's [TechnologyCostOfCapital](fleet.md#technologycostofcapital), when set, replaces it as the discount rate of the technology adoption decision.

* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `0.1`
  + `Forecast("name")`
* **Unit**: Fraction/year
* **Minimum value**: 0
* **Default**: 0
