# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EXTENSION - the four regulations also cover the regional ships (reg_*).
# Read after policy_gfs.inc and policy_eu.inc.

Regulation "gfs_tier_1" {
	set_include_vessel("reg_*", TRUE)
}

Regulation "gfs_tier_2" {
	set_include_vessel("reg_*", TRUE)
}

Regulation "eu_ets" {
	set_include_vessel("reg_*", TRUE)
}

Regulation "fuel_eu" {
	set_include_vessel("reg_*", TRUE)
}
