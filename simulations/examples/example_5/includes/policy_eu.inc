# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU ETS AND FUELEU - the library's own two regulations, with Martinique, an EU
# outermost region, as the one EU port.
#
# Both regulations count a leg (one sailing from one port to the next) in full
# between two EU ports and at half between an EU and a non-EU port. The
# exemptions for voyages within an outermost region (EU ETS until 2030, FuelEU
# until 2029 at the member state's request) touch only the regional ships, which
# are under 5,000 GT and outside both anyway.
#
# Both apply to ships of 5,000 GT and above, so they cover the international
# ships (intl_*) only. A deck that extends them to the regional ships adds
# set_include_vessel("reg_*", TRUE) after this file.

Import Regulation "eu_ets"
Import Regulation "fuel_eu"

Regulation "eu_ets" {
    Jurisdiction = [Port("martinique")]
    set_include_vessel("*", FALSE)
    set_include_vessel("intl_*", TRUE)
}

Regulation "fuel_eu" {
    Jurisdiction = [Port("martinique")]
    set_include_vessel("*", FALSE)
    set_include_vessel("intl_*", TRUE)
}
