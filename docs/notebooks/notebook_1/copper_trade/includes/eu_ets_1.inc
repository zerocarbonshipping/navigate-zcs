# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU_ETS = 1 - EU ETS covers every ship, as in eu_ets.inc.

Regulation "eu_ets" {
    set_include_vessel("*", TRUE)
}
