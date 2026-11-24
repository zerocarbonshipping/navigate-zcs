# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU_RULES_WHOLE_VOYAGE = 0 - Rotterdam only, as in eu_ets.inc and fuel_eu.inc: both
# legs are inter-jurisdiction voyages and count at 50%.

Regulation "eu_ets" {
    Jurisdiction = [Port("rotterdam")]
}

Regulation "fuel_eu" {
    Jurisdiction = [Port("rotterdam")]
}
