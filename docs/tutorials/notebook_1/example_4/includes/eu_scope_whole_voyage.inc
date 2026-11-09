# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU SCOPE - San Antonio inside both schemes too: both legs become
# intra-jurisdiction voyages, so IntraFraction = 1 counts the whole voyage.

Regulation "eu_ets" {
    Jurisdiction = [Port("rotterdam"), Port("san_antonio")]
}

Regulation "fuel_eu" {
    Jurisdiction = [Port("rotterdam"), Port("san_antonio")]
}
