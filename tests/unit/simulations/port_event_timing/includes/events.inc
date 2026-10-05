# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# From 01-01-2028 on, oil_cheap costs 500 + 1000 = 1500 USD/ton against
# oil_dear's 600 USD/ton.
Start
Date "01-01-2027"
Date "01-01-2028"

Port "*" {
	set_handling_cost("oil_cheap", 1000)                           # USD/ton
}

Date "01-01-2029"
End
