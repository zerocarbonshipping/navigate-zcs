# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: WTT methane emissions from natural gas.
# Unit: ton methane / ton feedstock
# Low-end benchmark (~3 gCO2eq/MJ total WTT, avg of Norwegian pipeline
# and BC Canada best practice). Blue ammonia producers selecting CCS would
# also source low-emission natural gas.

Forecast "natural_gas_wtt_methane" {
    Table = [
        "01-01-2025"    0.0031
        "01-01-2050"    0.0031
    ]
}