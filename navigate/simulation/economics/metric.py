# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Discounting metrics over yearly flows: net present value and levelized cost."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.economics.flows import get_flow_size

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


def calculate_age_levelized_cost(
    cost_flow: FloatArray, lifetime: float, discount_rate: float
) -> float:
    """
    Calculate a cost levelized over the years of an asset's lifetime.

    Parameters
    ----------
    cost_flow
        Cost per year of age.
    lifetime
        Lifetime of the asset, in years.
    discount_rate
        Discount rate, the return on an alternative investment, in fraction/year.

    Returns
    -------
    float
        Discounted cost per discounted year of lifetime.
    """
    age_flow = np.ones(get_flow_size(lead_time=0.0, lifetime=lifetime))
    return calculate_levelized_cost(cost_flow, age_flow, discount_rate)


def calculate_levelized_cost(
    cost_flow: FloatArray, level_flow: FloatArray, discount_rate: float
) -> float:
    """
    Calculate the present cost per present unit of a leveling flow.

    Parameters
    ----------
    cost_flow
        Cost per year.
    level_flow
        Quantity per year the cost is levelized over, such as production.
    discount_rate
        Discount rate, the return on an alternative investment, in fraction/year.

    Returns
    -------
    float
        Levelized cost.
    """
    net_present_cost = calculate_net_present_value(cost_flow, discount_rate)
    net_present_level = calculate_net_present_value(level_flow, discount_rate)
    return net_present_cost / net_present_level


def calculate_net_present_value(flow: FloatArray, discount_rate: float) -> float:
    """
    Calculate the net present value of a yearly flow, year 0 undiscounted.

    Parameters
    ----------
    flow
        Value per year.
    discount_rate
        Discount rate, the return on an alternative investment, in fraction/year.

    Returns
    -------
    float
        The sum of discounted values.
    """
    years = np.arange(len(flow))
    return float(np.sum(flow / (1.0 + discount_rate) ** years))
