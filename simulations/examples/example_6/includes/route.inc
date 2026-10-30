# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ROUTE - Rhine, Duisburg - Cologne - Koblenz - Mainz - Mannheim, then straight
# back to Duisburg. Each entry is the leg (one-way sailing to the next port)
# leaving the port at that index. ALL values below are INVENTED placeholders.

Vessel "rhine_*" {
	Route = Route("rhine_route")
}

Route "rhine_route" {
	RouteType = ROUND_TRIP

	Ports = [Port("duisburg"), Port("cologne"), Port("koblenz"), Port("mainz"), Port("mannheim")]

	# INVENTED: one day in port per call
	PortDurations = [1, 1, 1, 1, 1]

	# INVENTED: nautical miles; the last leg is Mannheim back to Duisburg
	Distances = [50, 52, 51, 40, 193]

	# INVENTED: 7 kn upstream, 8 kn back (speed through the water, no current)
	Speeds = [7, 7, 7, 7, 8]

	# INVENTED: a quarter of the cargo discharged at each of Cologne, Koblenz and
	# Mainz, the rest at Mannheim; ballast on the way back
	CapacityUtilizations = [1.0, 0.75, 0.5, 0.25, 0]
}
