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
    RouteType = ROUND_TRIP

    Ports = [Port("singapore"), Port("rotterdam")]
	PortDurations = [1.5, 1.0]

	Distances = [8300, 8300]
    Speeds = [15.5, 14.2]
    # Fully laden outbound, almost empty return
    CapacityUtilizations = [0.95, 0.1]
}

# Rotterdam to Hamburg to Aalborg
# This regional short-sea route connects Rotterdam with Hamburg and Aalborg.
# It is operated by 1,500 TEU feeder vessels.
#
# Hamburg, a major container port with advanced infrastructure, supports early adoption of alternative fuels.
# Aalborg, while smaller and less developed, represents a realistic challenge in fuel access and port services.

Route "feeder_route" {
    RouteType = ROUND_TRIP

    Ports = [Port("rotterdam"), Port("hamburg"), Port("aalborg")]
    PortDurations = [1.5, 1.0, 1.0]

    Distances = [270, 400, 800]
    Speeds = [13.0, 12.5, 13.0]
    # Full outbound, partial mid-leg, empty return
    CapacityUtilizations = [1.0, 0.7, 0.0]  
}
