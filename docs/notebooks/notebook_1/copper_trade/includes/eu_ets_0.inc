# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU_ETS = 0 - every ship taken out of EU ETS; FuelEU stays.

Regulation "eu_ets" {
    set_include_vessel("*", FALSE)
}
