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
    RouteType = REGIONAL_TRIP

    Ports = Port("*")               # there are five ports, number of port calls must match
    PortCalls = [11, 9, 8, 4, 4]    # 36 in total according to assumptions
 
    TimeAtSea = 0.47
    Speeds = [13.0, 12.5, 12.0, 11.8, 12.2]

    ConditionDistribution = [0.26, 0.21, 0.18, 0.17, 0.18]
}
