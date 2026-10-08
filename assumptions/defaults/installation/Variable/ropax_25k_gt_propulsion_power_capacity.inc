# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GENERATED FILE — DO NOT EDIT.
# Source record: assumptions/vessels/new_segments_design_parameters.yaml
# Repository: https://github.com/zerocarbonshipping/assumptions
# Tier 3 | status: provisional | provenance: derived | unit: per variant suffix: nominal_capacity in the segment unit (chemical tanker dwt; LNG and LPG carrier m3 of cargo; ro-pax and small ferry GT); propulsion_power_capacity and electrical_power_capacity in MW installed; tank_size in m3 of fuel
# Design parameters of a typical buildable ship for each of the five segments added by segment taxonomy v1: nominal cargo capacity, installed propulsion and electrical power, and fuel tank volume. Reference-vessel convention (fleet pipeline D13, proposed): the value is that of a public reference vessel near the segment anchor size, cross-checked against the IMO GHG4 2018 fleet mean of the matching size bin. Variant keys are <segment>.<parameter>. Parameters with no public source (heat power capacity; tank size of the chemical tanker, LPG carrier and small ferry; electrical capacity of the LPG carrier) are NOT in this record: their Navigate leaves are inherited from the parent segment and listed as open in the worklog - except where the parent value is below the segment's own load, where a placeholder capacity = peak GHG4 load is set here (see processing).

Variable "ropax_25k_gt_propulsion_power_capacity" {
	Value = 16
}
