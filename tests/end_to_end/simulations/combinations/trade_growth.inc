# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the base fleet at another trade growth. The %name% value is filled
# in by tests/end_to_end/test_orderbook_surplus.py.
Fleet "container_15000_teu" {
	TradeGrowth = %trade_growth%                # fraction/year
}
