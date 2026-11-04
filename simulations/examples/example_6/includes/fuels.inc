# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUELS - all five are market fuels, bought at the bunker ports at a set price
# with set upstream emissions (includes/ports.inc). Nothing is made in the deck,
# so it has no region, plant or producer.

# ---- market fuels -----------------------------------------------------------
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"
Import Fuel "fatty_acid_methyl_ester"
Import Fuel "diesel_electro"
Import Fuel "methanol_electro"

# ---- fuels named by the copied regulation but not used by this case ---------
# (imported only so that Regulation "co2_price_germany" parses)
Import Fuel "methanol_bio"
Import Fuel "methane_bio"
Import Fuel "methane_electro"
Import Fuel "ammonia_blue"
Import Fuel "ammonia_electro"
