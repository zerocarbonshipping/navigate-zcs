# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ROUTE - San Antonio to Rotterdam and back via the Panama Canal.
# A LINER visits the ports in the order listed; each per-leg command is keyed by
# the leg's origin and destination ports.

Vessel "ship_*" {
    Route = Route("copper_route")
}

Route "copper_route" {
    RouteType = LINER

    Ports = [Port("san_antonio"), Port("rotterdam")]

    # Days alongside per call, from the library's operational profile for this
    # class: TimeAtSea 0.55 over 24 calls/year = 0.45 x 365 / 24.
    set_port_duration("*", "*", 6.8)

    # The distances for this example are invented since this route geography
    # is not included in the Navigate Assumption.
    set_distance("*", "*", 7600)

    # Modal service speed from the library's operational profile for this ship class.
    set_speed("*", "*", 11.5)

    # Laden out, ballast home.
    set_utilization("san_antonio", "rotterdam", 1.0)
    set_utilization("rotterdam", "san_antonio", 0.0)
}
