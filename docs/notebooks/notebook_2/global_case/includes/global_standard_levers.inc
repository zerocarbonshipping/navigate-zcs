# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The global fuel standard's levers; under 1, GLOBAL_STANDARD_TARGET is stricter.

Regulation "gfs" {
    set_vessel_threshold("*", <Forecast("gfs_target_reduction") * %GLOBAL_STANDARD_TARGET%>)
}

Forecast "gfs_remedial_unit" {
    Multiplier = %GLOBAL_STANDARD_PENALTY%
}
