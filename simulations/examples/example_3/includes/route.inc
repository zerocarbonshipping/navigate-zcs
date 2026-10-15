# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ ROUTES ---------------------------------------
#
# This file defines the transport routes used in the Baltic tanker scenario. 
# Two separate route structures are included, reflecting the different roles 
# of the coastal tankers (~7.5k DWT) and the MR tankers (~47k DWT).
#
# The coastal tankers operate primarily on short-sea trades linking Helsinki, 
# Tallinn, and Stockholm. These vessels are suited to frequent, shorter legs 
# and to ports with more limited draft. Their operation emphasizes port time 
# and short sailing intervals.
#
# The MR tankers connect Helsinki and Stockholm with Gdansk. These vessels 
# handle larger parcels and cover longer legs across the Baltic, where they 
# spend a greater fraction of time at sea. MR tankers are also the first to 
# test the uptake of e-ammonia bunkering at major hubs.
#
# Separating the coastal and MR routes makes it possible to capture differences 
# in operational profile, fuel consumption, and bunkering constraints while 
# keeping both fleets within the same regional trade network.
#
# ----------------------------------------------------------------------------

Vessel "mid_range_*" {
    Route = Route("mid_range_route")
}

Vessel "coastal_*" {
    Route = Route("coastal_route")
}

# MR loop: Helsinki - Stockholm - Gdansk
# Longer legs, larger vessels, more time at sea
Route "mid_range_route" {
    RouteType = TRAMP

    Ports = [Port("helsinki"), Port("stockholm"), Port("gdansk")]
    set_port_calls("helsinki", 12)
    set_port_calls("stockholm", 10)
    set_port_calls("gdansk", 14)

    TimeAtSea = 0.55
    set_voyage_distribution("*", "*", 1)

    set_speed("*", "*", Curve("speed_distribution_mid_range_route"))
}

# Coastal loop: Helsinki - Tallinn - Stockholm
# Short legs, frequent port calls, higher share of port time
Route "coastal_route" {
    RouteType = TRAMP

    Ports = [Port("helsinki"), Port("tallinn"), Port("stockholm")]
    set_port_calls("helsinki", 14)
    set_port_calls("tallinn", 12)
    set_port_calls("stockholm", 10)

    TimeAtSea = 0.40
    set_voyage_distribution("*", "*", 1)

    set_speed("*", "*", Curve("speed_distribution_coastal_route"))
}

# Share of the time at sea sailed at each speed (x = knots ; y = fraction)
Curve "speed_distribution_mid_range_route" {
    Table = [
        12.5    0.38
        12.8    0.34
        13.0    0.28
    ]
}

Curve "speed_distribution_coastal_route" {
    Table = [
        11.0    0.30
        11.2    0.30
        11.5    0.40
    ]
}
