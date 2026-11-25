# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU_RULES_WORLDWIDE = 0 - the EU rules cover the voyages that touch Europe, as in the
# scenario.

Regulation "eu_ets" {
    Jurisdiction = [Port("port_europe")]
}

Regulation "fuel_eu" {
    Jurisdiction = [Port("port_europe")]
}
