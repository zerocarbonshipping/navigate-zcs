# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ROUTE - San Antonio to Rotterdam and back via the Panama Canal.
# ROUND_TRIP visits the ports in the order listed; each entry in
# Distances/Speeds/CapacityUtilizations is the leg leaving the port at that index.

Vessel "ship_*" {
    Route = Route("copper_route")
}

Route "copper_route" {
    RouteType = ROUND_TRIP

    Ports = [Port("san_antonio"), Port("rotterdam")]

    # Days alongside per call, from the library's operational profile for this
    # class: TimeAtSea 0.55 over 24 calls/year = 0.45 x 365 / 24.
    PortDurations = [6.8, 6.8]

    # The distances for this example are invented since this route geography
    # is not included in the Navigate Assumption.
    Distances = [7600, 7600]

    # Modal service speed from the library's operational profile for this ship class.
    Speeds = [11.5, 11.5]

    # Laden out, ballast home.
    CapacityUtilizations = [1.0, 0.0]
}
