# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ ROUTE -------------------------------------------
#
# This file defines the transport routes in the example, representing
# regional bulk trade across the South Pacific. The network connects
# the main hubs (Australia and New Zealand) with island ports (Fiji, 
# Samoa, and Tonga). This is a tramp route and thus the ports are not
# visited in any particular order.
#
# --------------------------------------------------------------------------------

Vessel "bulk_carrier_handysize_oil" {
    Route = Route("pacific_trade")
}

Route "pacific_trade" {
    RouteType = TRAMP

    Ports = Port("*")               # the five ports of ports.inc

    # 36 port calls in total according to assumptions
    set_port_calls("australia", 11)
    set_port_calls("new_zealand", 9)
    set_port_calls("fiji", 8)
    set_port_calls("samoa", 4)
    set_port_calls("tonga", 4)

    TimeAtSea = 0.47
    set_voyage_distribution("*", "*", 1)

    set_speed("*", "*", Curve("speed_distribution_pacific_trade"))
}

# Share of the time at sea sailed at each speed (x = knots ; y = fraction)
Curve "speed_distribution_pacific_trade" {
    Table = [
        11.8    0.17
        12.0    0.18
        12.2    0.18
        12.5    0.21
        13.0    0.26
    ]
}
