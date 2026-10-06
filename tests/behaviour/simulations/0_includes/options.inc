# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Pin the LP backend so results do not depend on a Gurobi license being present.
BunkerOptions {
	Solver = HIGHS
}
