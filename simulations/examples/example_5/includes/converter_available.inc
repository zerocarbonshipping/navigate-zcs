# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# WHEN THE NEW ENGINES CAN BE ORDERED - the library's DefaultConverterAvailable
# dates for each class, under this deck's fleet names (its patterns, "tug*" and
# the like, do not match them).

Start

Fleet "*" {
	set_allow_vessel("*ammonia*", FALSE)
	set_allow_vessel("*methanol*", FALSE)
}

Fleet "reg_tug" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "reg_ferry" {
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "intl_feeder" {
	set_allow_vessel("*methanol*", TRUE)
}

Date "01-01-2027"

Fleet "reg_tug" {
	set_allow_vessel("*ammonia*", TRUE)
}

Fleet "intl_feeder" {
	set_allow_vessel("*ammonia*", TRUE)
}

Date "01-01-2030"

Fleet "reg_tanker" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

Fleet "reg_cargo" {
	set_allow_vessel("*ammonia*", TRUE)
	set_allow_vessel("*methanol*", TRUE)
}

End
