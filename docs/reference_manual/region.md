<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Region

A `Region` node defines a region of the world for fuel production and the cost, emissions, etc., associated
with production in that region. Examples of regions are Africa and the Middle East.

Example:

```python
Region "africa" {
    # set process
    set_process_capex("methane_synthesis_electro", 500)
    set_process_opex("methane_synthesis_electro", 50)
    set_process_energy("methane_synthesis_electro", 3.7)
    set_process_wtt("carbon_dioxide_biogenic", "carbon_dioxide", -1)
    
    # source
    set_source_capex("renewable", 50)
    set_source_opex("renewable", 50)
    
    # set WTT process emissions below:
    set_source_wtt("renewable", "carbon_dioxide", 0.005)
    
    # feedstock
    set_feedstock_cost("organic_wet_waste", 150)
    set_feedstock_wtt("organic_wet_waste", "carbon_dioxide", 0.5)
    
    # transport
    set_transport_cost("truck", 45)
    set_transport_wtt("truck", "carbon_dioxide", 0.5)
}
```

## Commands

### set\_process\_capex

This command sets the CAPEX associated with a production process in USD/ton.

* **Primary key type**: String (Process name)
* **Data type**: `Float`, `Forecast`, `Timetable`, `Variable`
* **Example values**:
  + `"process_name", 500`
  + `"process_name", Forecast("name")`
* **Unit**: USD/ton
* **Minimum value**: 0
* **Default**: 0

### set\_process\_opex

This command sets the OPEX associated with a production process in USD/ton/year.

* **Primary key type**: String (Process name)
* **Data type**: `Float`, `Forecast`, `Timetable`, `Variable`
* **Example values**:
  + `"process_name", 50`
  + `"process_name", Forecast("name")`
* **Unit**: USD/ton/year
* **Minimum value**: 0
* **Default**: 0

### set\_process\_energy

This command sets the energy demand required to run a production process in MWh/ton.

* **Primary key type**: String (Process name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"process_name", 3.7`
  + `"process_name", Forecast("name")`
* **Unit**: MWh/ton
* **Minimum value**: 0
* **Default**: 0

### set\_process\_lifetime

This command sets the lifetime of a production process in years.

* **Primary key type**: String (Process name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"process_name", 25`
  + `"process_name", Forecast("name")`
* **Unit**: years
* **Minimum value**: 0
* **Default**: None

### set\_process\_replacement

This command sets the replacement fraction of CAPEX repaid at the end of a process's lifetime.

* **Primary key type**: String (Process name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"process_name", 0.5`
  + `"process_name", Forecast("name")`
* **Unit**: Fraction of CAPEX
* **Minimum value**: 0
* **Maximum value**: 1
* **Default**: 0

### set\_process\_wtt

This command sets the WTT emissions of a specific emission type emitted during a production process in ton emission/ton fuel.

* **Primary key type**: String (Process name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"process_name", "emission_name", 0.5`
  + `"process_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton fuel
* **Default**: None

### set\_source\_capex

This command sets the CAPEX associated with a source in USD/MWh.

* **Primary key type**: String (Source name)
* **Data type**: `Float`, `Forecast`, `Timetable`, `Variable`
* **Example values**:
  + `"source_name", 50`
  + `"source_name", Forecast("name")`
* **Unit**: USD/MWh
* **Minimum value**: 0
* **Default**: 0

### set\_source\_opex

This command sets the OPEX associated with a source in USD/MWh/year.

* **Primary key type**: String (Source name)
* **Data type**: `Float`, `Forecast`, `Timetable`, `Variable`
* **Example values**:
  + `"source_name", 50`
  + `"source_name", Forecast("name")`
* **Unit**: USD/MWh/year
* **Minimum value**: 0
* **Default**: 0

### set\_source\_wtt

This command sets the WTT emissions of a specific emission type emitted by using a source in ton emission/MWh.

* **Primary key type**: String (Source name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"source_name", "emission_name", 0.5`
  + `"source_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/MWh
* **Default**: None

### set\_feedstock\_cost

This command sets the cost of a feedstock in USD/ton.

* **Primary key type**: String (Feedstock name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"feedstock_name", 45`
  + `"feedstock_name", Forecast("name")`
* **Unit**: USD/ton
* **Minimum value**: 0
* **Default**: 0

### set\_feedstock\_wtt

This command sets the WTT emissions of a specific emission type emitted by using the feedstock in ton emission/ton.

* **Primary key type**: String (Feedstock name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"feedstock_name", "emission_name", 0.5`
  + `"feedstock_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton
* **Default**: None

### set\_transport\_cost

This command sets the cost associated with a transport in USD/ton-nautical mile.

* **Primary key type**: String (Transport name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"transport_name", 45`
  + `"transport_name", Forecast("name")`
* **Unit**: USD/ton-nautical miles
* **Minimum value**: 0
* **Default**: 0

### set\_transport\_wtt

This command sets the WTT emissions of a specific emission emitted by using a transport in ton emission/ton-nautical mile.

* **Primary key type**: String (Transport name)
* **Secondary key type**: String (Emission name)
* **Data type**: `Float`, `Forecast`, `Variable`
* **Example values**:
  + `"transport_name", "emission_name", 0.5`
  + `"transport_name", "emission_name", Forecast("name")`
* **Unit**: ton emission/ton-nautical mile
* **Default**: None
