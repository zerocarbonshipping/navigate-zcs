# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GLOBAL_STANDARD = 1 - the global fuel standard covers every ship, as in the scenario.

Regulation "gfs" {
    set_include_vessel("*", TRUE)
}
