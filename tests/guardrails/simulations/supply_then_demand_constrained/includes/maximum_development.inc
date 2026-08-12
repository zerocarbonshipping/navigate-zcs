# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# The single deviation from the supply_constrained deck: MaximumDevelopment
# raised so supply catches up with demand roughly halfway through the
# simulation (deck-sizing input, tuned; CATCHUP_STEP in the test module was
# derived from this value's tuning run).
Producer "epc_europe" {
	MaximumDevelopment = 3
}
