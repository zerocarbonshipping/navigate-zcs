# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GLOBAL_STANDARD = 0 - every ship taken out of the global fuel standard; the other regulations stay.

Regulation "gfs" {
    set_include_vessel("*", FALSE)
}
