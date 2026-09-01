# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.economics.flows import get_age_flow


def calculate_age_levelized_cost(cost_flow, lifetime, discount_rate):
    """
    Calculate the levelized cost of age.

    Parameters
    ----------
    cost_flow : np.ndarray
        The cost-flow.
    lifetime : float
        Lifetime of the vessel.
    discount_rate : float
        Discount rate representing the return on alternative investment.

    Returns
    -------
    float
        Yearly average net present cost.
    """

    time_steps = get_age_flow(lead_time=0, lifetime=lifetime)
    return calculate_levelized_cost(cost_flow, time_steps, discount_rate)


def calculate_levelized_cost(cost_flow, level_flow, discount_rate):
    """
    Calculate the levelized cost according to some leveling metric.

    Parameters
    ----------
    cost_flow : np.ndarray
        The cost-flow.
    level_flow : np.ndarray
        The leveling-flow.
    discount_rate : float
        Discount rate representing the return on alternative investment.

    Returns
    -------
    float
        Levelized cost.
    """

    net_present_cost = calculate_net_present_value(cost_flow, discount_rate)
    net_present_level = calculate_net_present_value(level_flow, discount_rate)

    return net_present_cost / net_present_level


def calculate_net_present_value(values, discount_rate):
    """
    Calculates the net present value of a property.

    Parameters
    ----------
    values : np.ndarray
        Values for which to calculate the net present value.
    discount_rate : float
        Discount rate representing the return on alternative investment, fraction/year.

    Returns
    -------
    float
       The sum of discounted values.
    """

    return float(np.sum(_discount_values(values, discount_rate)))


def _discount_values(values, discount_rate):
    """
    Discounts values along a time dimension according to a specific discount factor.

    Parameters
    ----------
    values : np.ndarray
        Values to be discounted.
    discount_rate : float
        Discount rate representing the return on alternative investment, fraction/year.

    Returns
    -------
    np.ndarray
        Discounted values.
    """

    return values / ((1. + discount_rate) ** np.arange(len(values)))
