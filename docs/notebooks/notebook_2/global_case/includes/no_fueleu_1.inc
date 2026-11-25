# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# NO_FUELEU = 1 - every ship taken out of FuelEU; the other regulations stay.

Regulation "fuel_eu" {
    set_include_vessel("*", FALSE)
}
