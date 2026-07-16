# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: WTT carbon dioxide emissions from LNG.
# Unit: ton carbon dioxide / ton fuel

Forecast "liquefied_natural_gas_wtt_carbon_dioxide" {
    Table = [
        "01-01-2025"    0.7 # 0.59 for liquefaction + 0.11 for upstream
        "01-01-2050"    0.7
    ]
}