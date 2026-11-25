# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# NO_EU_ETS = 1 - every ship taken out of EU ETS; the other regulations stay.

Regulation "eu_ets" {
    set_include_vessel("*", FALSE)
}
