# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FREEZE_EFFICIENCY = 0 - the share of the fleet that may fit each efficiency
# technology in a year, on newbuilds and on retrofits, is Navigate's default, 1.
# Only these segments' fleets have efficiency technologies.

Fleet "bulk_carrier_*" {
    set_newbuild_technology_limit("*", 1)
    set_retrofit_technology_limit("*", 1)
}

Fleet "container_*" {
    set_newbuild_technology_limit("*", 1)
    set_retrofit_technology_limit("*", 1)
}

Fleet "gas_carrier_*" {
    set_newbuild_technology_limit("*", 1)
    set_retrofit_technology_limit("*", 1)
}

Fleet "roro_*" {
    set_newbuild_technology_limit("*", 1)
    set_retrofit_technology_limit("*", 1)
}

Fleet "tanker_*" {
    set_newbuild_technology_limit("*", 1)
    set_retrofit_technology_limit("*", 1)
}
