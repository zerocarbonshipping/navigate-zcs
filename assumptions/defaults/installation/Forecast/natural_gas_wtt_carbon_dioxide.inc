# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: WTT carbon dioxide emissions from natural gas.
# Unit: ton carbon dioxide / ton feedstock
# Low-end benchmark (~3 gCO2eq/MJ total WTT, avg of Norwegian pipeline
# and BC Canada best practice). Blue ammonia producers selecting CCS would
# also source low-emission natural gas.

Forecast "natural_gas_wtt_carbon_dioxide" {
    Table = [
        "01-01-2025"    0.058
        "01-01-2050"    0.058
    ]
}
