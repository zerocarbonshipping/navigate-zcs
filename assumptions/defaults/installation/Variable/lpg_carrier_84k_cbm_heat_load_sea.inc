# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GENERATED FILE — DO NOT EDIT.
# Source record: assumptions/vessels/new_segments_operational_loads.yaml
# Repository: https://github.com/zerocarbonshipping/assumptions
# Tier 3 | status: provisional | provenance: sourced | unit: MW (average power output per vessel)
# Average auxiliary-engine (electrical) and boiler (heat) power output of a vessel at sea and in port, in MW, for the five segments added by segment taxonomy v1: chemical_tanker_40k_dwt, lng_carrier_174k_cbm, lpg_carrier_84k_cbm, ropax_25k_gt, ferry_small_2k_gt. Consumed by the Vessel nodes (ElectricalLoadAtSea/InPort, HeatLoadAtSea/InPort). One public table (IMO Fourth GHG Study, Table 17) gives the values per ship type and size bin; the segment value is the row of the bin that holds the segment reference vessel. Variant keys are <segment>.<load>. Tier 3 because the bin choice (reference bin vs fleet-weighted mix of bins, convention D13 pending) is a judgment and the table is a modelling assumption of the study, not a measurement.

Variable "lpg_carrier_84k_cbm_heat_load_sea" {
	Value = 0.1
}
