# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The EU ETS price, and FuelEU's limit and penalty; the EU rules' switches are
# the files the deck picks with %EU_ETS%, %FUELEU% and %EU_WORLDWIDE%.

Import Forecast "eu_ets_carbon_credit_price"
Forecast "eu_ets_carbon_credit_price" {
    Multiplier = %EU_ETS_PRICE%
}

# the limit's forecast has a Multiplier of its own (91.16), so the lever scales
# the threshold: under 1 is stricter
Regulation "fuel_eu" {
    set_vessel_threshold("*", <Forecast("fuel_eu_target_reduction") * %FUELEU_TARGET%>)
    RemedialCost = <Variable("fuel_eu_remedial_cost") * %FUELEU_PENALTY%>
}
