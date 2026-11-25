# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# NO_GLOBAL_STANDARD = 1 - every ship taken out of the global fuel standard; the other
# regulations stay.

Regulation "gfs" {
    set_include_vessel("*", FALSE)
}
