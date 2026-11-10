# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
An orderbook leaves a fleet in surplus unchanged.

An orderbook delivers the increase over the orders already delivered or
postponed (docs/reference_manual/fleet.md, Orderbooks), and postpones the
orders the trade gap leaves no room for (calculate_orderbook_newbuilds in
navigate/simulation/fleet/_newbuild.py); secondary scrapping removes a surplus
(AllowSecondaryScrapping, TRUE by default). While a fleet's trade falls faster
than age scrapping removes vessels, the fleet holds a surplus at every step,
so no due order can be delivered and secondary scrapping cuts the fleet to its
trade. With or without the orderbook, the fleet is the same.
"""

from __future__ import annotations

import numpy as np
import pytest

FLEET = "container_15000_teu"

# fraction/year: a fifth of the trade lost each year, far faster than age
# scrapping removes the base fleet's vessels
TRADE_GROWTH = -0.2

# oil vessels on order, a tenth of the base fleet, all due from the start
OIL_ORDERS = 50


def _fleet(run_combination, *layers):
    trade = ("trade_growth.inc", {"trade_growth": TRADE_GROWTH})
    return run_combination(trade, *layers).nodes.fleets[FLEET]


def _total(per_vessel):
    return sum(per_vessel.values())


def test_an_orderbook_leaves_a_fleet_in_surplus_unchanged(run_combination):
    secondary_scrapping = {"allow_secondary_scrapping": "FALSE"}
    orderbooks = {"oil_orders": OIL_ORDERS}

    without = _fleet(run_combination)
    barred = _fleet(run_combination, ("secondary_scrapping.inc", secondary_scrapping))
    ordered = _fleet(run_combination, ("orderbooks.inc", orderbooks))

    # barred from secondary scrapping, the fleet scraps by age alone, and at
    # least as much by age as the fleet that also scraps its oldest vessels for
    # a surplus; scrapping more than it means a surplus at every step after the
    # first, which only records the initial fleet
    scrap = _total(without.results.scrap)[1:]
    scrap_by_age = _total(barred.results.scrap)[1:]
    assert np.all(scrap > scrap_by_age), "the fleet must be in surplus"

    # by the end of the horizon, every order is delivered or postponed
    booked = np.sum(ordered.orders_delivered + ordered.orders_postponed)
    assert booked == pytest.approx(OIL_ORDERS), "the orders must fall due"

    for vessel, newbuilds in ordered.results.newbuilds.items():
        assert not np.any(newbuilds), vessel

    # a delivery of exactly zero leaves the two runs on identical arithmetic
    expected = without.results.existing_vessels
    for vessel, existing in ordered.results.existing_vessels.items():
        np.testing.assert_array_equal(existing, expected[vessel], err_msg=vessel)
