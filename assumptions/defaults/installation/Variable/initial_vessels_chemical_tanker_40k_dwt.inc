# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GENERATED FILE — DO NOT EDIT.
# Source record: assumptions/vessels/new_segments_fleet_counts.yaml
# Repository: https://github.com/zerocarbonshipping/assumptions
# Tier 3 | status: provisional | provenance: derived | unit: number of vessels (initial_vessels); cumulative number of vessels delivered from 2025 (orderbook)
# Number of vessels in each of the five taxonomy-v1 segments at the start of the simulation (Fleet.InitialVessels), and the committed newbuild orderbook where a public source gives one (LNG carriers only). Public sources only: IMO GHG4 Table 35 counts per type and size bin (2018) for four segments; IGU World LNG Report 2025 for LNG carriers (end-2024). No public orderbook by delivery year exists for chemical tankers, LPG carriers or ferries; those leaves are open (worklog). Variant keys are <segment>.initial_vessels and lng_carrier_174k_cbm.orderbook_methane.

Variable "initial_vessels_chemical_tanker_40k_dwt" {
	Value = 5100
}
