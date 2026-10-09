# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Discounting metrics over yearly flows: net present value and levelized cost."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.simulation.economics.flows import get_age_flow

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


def calculate_age_levelized_cost(
    cost_flow: FloatArray, lifetime: float, discount_rate: float
) -> float:
    """
    Calculate the levelized cost of age.

    Parameters
    ----------
    cost_flow
        The cost-flow.
    lifetime
        Lifetime of the vessel.
    discount_rate
        Discount rate representing the return on alternative investment.

    Returns
    -------
    float
        Yearly average net present cost.
    """
    time_steps = get_age_flow(lead_time=0.0, lifetime=lifetime)
    return calculate_levelized_cost(cost_flow, time_steps, discount_rate)


def calculate_levelized_cost(
    cost_flow: FloatArray, level_flow: FloatArray, discount_rate: float
) -> float:
    """
    Calculate the levelized cost according to some leveling metric.

    Parameters
    ----------
    cost_flow
        The cost-flow.
    level_flow
        The leveling-flow.
    discount_rate
        Discount rate representing the return on alternative investment.

    Returns
    -------
    float
        Levelized cost.
    """
    net_present_cost = calculate_net_present_value(cost_flow, discount_rate)
    net_present_level = calculate_net_present_value(level_flow, discount_rate)

    return net_present_cost / net_present_level


def calculate_net_present_value(values: FloatArray, discount_rate: float) -> float:
    """
    Calculate the net present value of a property.

    Parameters
    ----------
    values
        Values for which to calculate the net present value.
    discount_rate
        Discount rate representing the return on alternative investment, fraction/year.

    Returns
    -------
    float
        The sum of discounted values.
    """
    return float(np.sum(_discount_values(values, discount_rate)))


def _discount_values(values: FloatArray, discount_rate: float) -> FloatArray:
    """
    Discounts values along a time dimension according to a specific discount factor.

    Parameters
    ----------
    values
        Values to be discounted.
    discount_rate
        Discount rate representing the return on alternative investment, fraction/year.

    Returns
    -------
    FloatArray
        Discounted values.
    """
    return values / ((1.0 + discount_rate) ** np.arange(len(values)))
