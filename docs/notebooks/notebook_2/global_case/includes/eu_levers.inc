# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The EU ETS price; the EU rules' switches are the files the deck picks with
# %EU_ETS%, %FUELEU% and %EU_WORLDWIDE%.

Import Forecast "eu_ets_carbon_credit_price"
Forecast "eu_ets_carbon_credit_price" {
    Multiplier = %EU_ETS_PRICE%
}
