# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Layered on top of ../0_includes/ports_oil_ammonia.inc (included first by
# the .nav): adds the LNG and methanol fuels this deck also offers. Prices
# and WTT are pinned constants (rounded from the 2026-08-13 installation
# defaults); without a Regulation or Levy the WTT values carry no cost, but
# they keep the deck's emission accounting honest.
Port "*" {
	set_bunkering_allowed("liquefied_natural_gas", TRUE)
	set_bunkering_allowed("methanol_bio", TRUE)

	set_bunker_price_overwrite("liquefied_natural_gas", 436)                  # USD/ton
	set_bunker_wtt_overwrite("liquefied_natural_gas", "carbon_dioxide", 0.7)  # ton/ton fuel
	set_bunker_wtt_overwrite("liquefied_natural_gas", "methane", 0.0073)

	# bio-methanol: biogenic carbon uptake credited upstream
	set_bunker_wtt_overwrite("methanol_bio", "carbon_dioxide", -1.38)
}
