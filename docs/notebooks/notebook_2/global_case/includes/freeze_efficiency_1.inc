# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FREEZE_EFFICIENCY = 1 - nothing further gets fitted: no efficiency technology
# on newbuilds or on retrofits.

Fleet "bulk_carrier_*" {
    set_newbuild_technology_limit("*", 0)
    set_retrofit_technology_limit("*", 0)
}

Fleet "container_*" {
    set_newbuild_technology_limit("*", 0)
    set_retrofit_technology_limit("*", 0)
}

Fleet "gas_carrier_*" {
    set_newbuild_technology_limit("*", 0)
    set_retrofit_technology_limit("*", 0)
}

Fleet "roro_*" {
    set_newbuild_technology_limit("*", 0)
    set_retrofit_technology_limit("*", 0)
}

Fleet "tanker_*" {
    set_newbuild_technology_limit("*", 0)
    set_retrofit_technology_limit("*", 0)
}
