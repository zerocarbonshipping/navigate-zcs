# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUELEU = 1 - FuelEU covers every ship, as in fuel_eu.inc.

Regulation "fuel_eu" {
    set_include_vessel("*", TRUE)
}
