# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Start

# Disable methanol and ammonia vessels for all fleets.
# These will subsequently be allowed during the timeline
# when the fuel technology is expected to become available.
Fleet "*" {
	set_allow_vessel("*ammonia*", FALSE)
	set_allow_vessel("*methanol*", FALSE)
	set_allow_vessel("*electric*", FALSE)
}

# Tug: battery-electric viable from start (harbor operations)
Fleet "tug*" {
	set_allow_vessel("*electric*", TRUE)
}

Fleet "bulk_carrier_200k_dwt*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "container_*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "tanker_127k_dwt*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "tanker_300k_dwt*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "cruise_*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "ferry*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "roro_*" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "tug*" {
	set_allow_vessel("*methanol*", TRUE)
}

Date "01-01-2027"
# Ammonia technology is expected for some ship
# types to be available from 2027 and onwards

Fleet "bulk_carrier_200k_dwt*" {
	set_allow_vessel("*ammonia*", TRUE)
}

Fleet "container_*" {
	set_allow_vessel("*ammonia*", TRUE)
}

Fleet "tanker_127k_dwt*" {
	set_allow_vessel("*ammonia*", TRUE)
}

Fleet "tanker_300k_dwt*" {
	set_allow_vessel("*ammonia*", TRUE)
}

Fleet "roro_*" {
	set_allow_vessel("*ammonia*", TRUE)
}

Fleet "tug*" {
	set_allow_vessel("*ammonia*", TRUE)
}

# Ferry, offshore, other: short-range segments, battery tech mature
Fleet "ferry*" {
	set_allow_vessel("*electric*", TRUE)
}

Fleet "offshore*" {
	set_allow_vessel("*electric*", TRUE)
}

Fleet "other*" {
	set_allow_vessel("*electric*", TRUE)
}

Date "01-01-2030"

Fleet "bulk_carrier_26k_*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "bulk_carrier_52k_*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "bulk_carrier_80k_dwt*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "tanker_7500_dwt*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "tanker_47k_dwt*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "gas_carrier_100k_cbm*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "general_cargo*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "offshore*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "other*" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

# General cargo: longer voyages, needs more battery capacity development
Fleet "general_cargo*" {
	set_allow_vessel("*electric*", TRUE)
}

End
