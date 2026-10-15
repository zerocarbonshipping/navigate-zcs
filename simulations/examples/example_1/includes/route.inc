# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ ROUTE -------------------------------------------
#
# This file defines the key transport routes in the example, covering:
# - A long-haul mainline route between Singapore and Rotterdam
# - A regional feeder roundtrip connecting Rotterdam, Hamburg, and Aalborg
#
# Each route includes realistic assumptions on distance, sailing time, vessel loading,
# port durations, and operational conditions—capturing both global and short-sea dynamics 
# within the same logistics network.
#
# --------------------------------------------------------------------------------

# Singapore to Rotterdam
# This long-haul round trip is operated by the mainline container vessel (~15,000 TEU).
# It covers approximately 8,300 nautical miles each way and includes turnaround time
# at both ends. Cargo is loaded from Singapore and returns almost empty from Europe.

Vessel "mainline_*" {
    Route = Route("mainline_route")
}

Vessel "feeder_*" {
    Route = Route("feeder_route")
}

Route "mainline_route" {
    RouteType = LINER

    Ports = [Port("singapore"), Port("rotterdam")]

    # A port duration is the time, in days, at the port that ends the leg.
    # Fully laden outbound, almost empty return
    set_distance("singapore", "rotterdam", 8300)
    set_speed("singapore", "rotterdam", 15.5)
    set_utilization("singapore", "rotterdam", 0.95)
    set_port_duration("singapore", "rotterdam", 1.0)

    set_distance("rotterdam", "singapore", 8300)
    set_speed("rotterdam", "singapore", 14.2)
    set_utilization("rotterdam", "singapore", 0.1)
    set_port_duration("rotterdam", "singapore", 1.5)
}

# Rotterdam to Hamburg to Aalborg
# This regional short-sea route connects Rotterdam with Hamburg and Aalborg.
# It is operated by 1,500 TEU feeder vessels.
#
# Hamburg, a major container port with advanced infrastructure, supports early adoption of alternative fuels.
# Aalborg, while smaller and less developed, represents a realistic challenge in fuel access and port services.

Route "feeder_route" {
    RouteType = LINER

    Ports = [Port("rotterdam"), Port("hamburg"), Port("aalborg")]

    # Full outbound, partial mid-leg, empty return
    set_distance("rotterdam", "hamburg", 270)
    set_speed("rotterdam", "hamburg", 13.0)
    set_utilization("rotterdam", "hamburg", 1.0)
    set_port_duration("rotterdam", "hamburg", 1.0)

    set_distance("hamburg", "aalborg", 400)
    set_speed("hamburg", "aalborg", 12.5)
    set_utilization("hamburg", "aalborg", 0.7)
    set_port_duration("hamburg", "aalborg", 1.0)

    set_distance("aalborg", "rotterdam", 800)
    set_speed("aalborg", "rotterdam", 13.0)
    set_utilization("aalborg", "rotterdam", 0.0)
    set_port_duration("aalborg", "rotterdam", 1.5)
}
