# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU_WORLDWIDE = 1 - port_global inside both EU schemes too: every voyage becomes
# an intra-jurisdiction voyage, so IntraFraction = 1 counts all of it.

Regulation "eu_ets" {
    Jurisdiction = [Port("port_global"), Port("port_europe")]
}

Regulation "fuel_eu" {
    Jurisdiction = [Port("port_global"), Port("port_europe")]
}
