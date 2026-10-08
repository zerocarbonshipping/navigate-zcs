# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GENERATED FILE — DO NOT EDIT.
# Source record: assumptions/vessels/new_segments_newbuild_capex_opex.yaml
# Repository: https://github.com/zerocarbonshipping/assumptions
# Tier 3 | status: provisional | provenance: derived | unit: USD2024 (capex variants, per vessel) and USD2024/yr (opex variants, per vessel)
# Newbuild price of the reference vessel (Vessel.CAPEX, USD) and its annual operating expenditure excluding fuel (Vessel.OPEX: crew, repairs and maintenance, insurance, stores, USD per year) for the five segments added by segment taxonomy v1. Flat 2025-2050. Evidence: public contract prices (listed-company filings, yard and project releases, broker reports) and operating cost per day from listed-company annual reports. Ro-pax opex has no public source and is NOT in this record (its leaf is inherited from the parent segment, listed as open in the worklog). Variant keys are <segment>.capex and <segment>.opex.

Forecast "lpg_carrier_84k_cbm_capex" {
	Table = [
		"01-01-2025"	110000000
		"01-01-2050"	110000000
	]
	Extrapolate = FLAT
}
