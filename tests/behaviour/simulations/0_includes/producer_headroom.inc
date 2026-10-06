# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Development headroom raised from fuel_supply_ammonia.inc's 1 plant/year,
# so e-ammonia supply can follow demand instead of trailing it for the whole
# horizon: the perturbation of the supply pair, and the base of the decks in
# which the policy signal, not the supply limit, must shape the fuel choice.
Producer "epc_europe" {
	MaximumDevelopment = 8
}
