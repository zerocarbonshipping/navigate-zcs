# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Discrete choice: multinomial-logit asset shares and two-axis uptake."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.util import define_index_map

if TYPE_CHECKING:
    from collections.abc import Hashable

    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)

# reference changes baked into the odds-ratio calibration. The log-ratio cases state the
# odds for a metric that is 10% higher; the signed case states the odds for an advantage
# equal to 5% of the reference value. The DSL exposes only the odds ratio; beta is
# derived from it here.
_REFERENCE_INCREASE = 0.10
_REFERENCE_ADVANTAGE = 0.05
_LOG_REFERENCE_INCREASE = np.log(1.0 + _REFERENCE_INCREASE)


def calculate_asset_shares(
    values: list[float] | FloatArray,
    utility: UtilityID,
    odds: float,
    reference: float | None = None,
    limits: list[float] | FloatArray | None = None,
) -> tuple[FloatArray, str]:
    """
    Calculate investment shares from a case-specific dimensionless utility.

    Routes `values` through the `utility` transformation and returns softmax shares;
    `limits`, when given, caps shares and rescales the surplus proportionally.

    Parameters
    ----------
    values
        Metric per alternative (LCOT, LCoF, expected demand, or NPV depending on
        `utility`).
    utility
        Utility transformation to apply.
    odds
        Odds ratio calibrating the sensitivity (e.g. 0.5 = a 10% higher metric gets half
        the odds).
    reference
        Reference value for `SIGNED_REFERENCE` (e.g. ship CAPEX); ignored by the
        log-ratio utilities.
    limits
        Optional per-option upper bound on share, each in [0, 1]. If None, no constraint
        is applied.

    Returns
    -------
    tuple[FloatArray, str]
        Asset investment shares and a potential warning message.
    """
    value_array = np.asarray(values, dtype=np.float64)
    beta = _beta_from_odds(odds, utility)

    if utility == UtilityID.LOWER_LOG_RATIO:
        shares, msg = _shares_lower_log_ratio(value_array, beta)
    elif utility == UtilityID.HIGHER_LOG_RATIO:
        shares, msg = _shares_higher_log_ratio(value_array, beta)
    else:
        shares, msg = _shares_signed_reference(value_array, beta, reference)

    if limits is not None:
        shares, limit_msg = _apply_limits(shares, limits)
        if limit_msg:
            msg = f"{msg}; {limit_msg}" if msg else limit_msg

    return shares, msg


def _beta_from_odds(odds: float, utility: UtilityID) -> float:
    """
    Convert an interpretable odds ratio into the multinomial-logit sensitivity beta.

    The reference change is fixed per utility kind: a 10% higher metric for the
    log-ratio cases and an advantage equal to 5% of the reference value for the signed
    case. An odds ratio of 1 yields beta = 0 (uniform shares); values on the wrong side
    of 1 yield beta < 0 (a perverse calibration).

    Parameters
    ----------
    odds
        Odds ratio (strictly positive; validated at the input level).
    utility
        Utility transformation the sensitivity is for.

    Returns
    -------
    float
        Sensitivity coefficient beta.
    """
    if utility == UtilityID.LOWER_LOG_RATIO:
        return float(-np.log(odds) / _LOG_REFERENCE_INCREASE)

    if utility == UtilityID.HIGHER_LOG_RATIO:
        return float(np.log(odds) / _LOG_REFERENCE_INCREASE)

    return float(np.log(odds) / _REFERENCE_ADVANTAGE)


def softmax(utilities: FloatArray) -> FloatArray:
    """
    Numerically stable softmax over deterministic utilities.

    Subtraction by the maximum value avoids exponential overflow while preserving the
    result.

    Parameters
    ----------
    utilities
        Deterministic utility per alternative.

    Returns
    -------
    FloatArray
        Probability of choice per alternative.
    """
    exp = np.exp(utilities - np.max(utilities))
    probabilities: FloatArray = exp / np.sum(exp)
    return probabilities


def _shares_lower_log_ratio(values: FloatArray, beta: float) -> tuple[FloatArray, str]:
    """
    Shares for a lower-is-better metric via V_i = -beta * log(value_i / min_j value_j).

    The log form requires strictly positive values. If any value is non-positive the
    form is undefined, so shares are split uniformly among the alternatives tied at the
    minimum value.

    Parameters
    ----------
    values
        Strictly-positive metric per alternative (lower is better).
    beta
        Sensitivity coefficient.

    Returns
    -------
    tuple[FloatArray, str]
        Shares per alternative and a potential warning message.
    """
    if np.any(values <= 0.0):
        msg = (
            "contains a non-positive value; the lower-is-better log-ratio utility is "
            "undefined, so shares were split uniformly among the alternatives at the "
            "minimum value"
        )
        return _uniform_at_min(values), msg

    utilities = -beta * np.log(values / np.min(values))
    return softmax(utilities), ""


def _shares_higher_log_ratio(values: FloatArray, beta: float) -> tuple[FloatArray, str]:
    """
    Shares for a higher-is-better metric via V_i = beta * log(value_i / max_j value_j).

    Alternatives with a value of zero receive zero share; the softmax is applied only to
    the strictly-positive alternatives. If every value is zero, all shares are zero (the
    caller is expected to short-circuit this case).

    Parameters
    ----------
    values
        Non-negative metric per alternative (higher is better, e.g. expected demand).
    beta
        Sensitivity coefficient.

    Returns
    -------
    tuple[FloatArray, str]
        Shares per alternative and a potential warning message.
    """
    shares = np.zeros_like(values)

    positive = values > 0.0
    if not np.any(positive):
        return shares, ""

    shares[positive] = softmax(
        beta * np.log(values[positive] / np.max(values[positive]))
    )
    return shares, ""


def _shares_signed_reference(
    values: FloatArray, beta: float, reference: float | None
) -> tuple[FloatArray, str]:
    """
    Shares for a signed metric scaled by reference via V_i = beta * value_i / reference.

    Handles positive, zero, or negative metrics (e.g. NPV). A non-positive reference
    makes the scaling undefined, so shares are split uniformly.

    Parameters
    ----------
    values
        Signed metric per alternative (e.g. NPV).
    beta
        Sensitivity coefficient.
    reference
        Strictly-positive reference value (e.g. ship CAPEX).

    Returns
    -------
    tuple[FloatArray, str]
        Shares per alternative and a potential warning message.
    """
    if (reference is None) or (reference <= 0.0):
        msg = "has a non-positive reference value; shares were split uniformly"
        return np.ones_like(values) / values.size, msg

    return softmax(beta * values / reference), ""


def _uniform_at_min(values: FloatArray) -> FloatArray:
    """
    Assign uniform shares among alternatives tied at the minimum value, zero elsewhere.

    Parameters
    ----------
    values
        Metric per alternative.

    Returns
    -------
    FloatArray
        Shares per alternative.
    """
    shares = np.zeros_like(values)

    at_min = values == np.min(values)
    shares[at_min] = 1.0 / np.count_nonzero(at_min)

    return shares


def _apply_limits(
    shares: FloatArray, limits: list[float] | FloatArray
) -> tuple[FloatArray, str]:
    """
    Enforce per-option upper bounds on a share vector, rescaling surplus proportionally.

    Parameters
    ----------
    shares
        Unconstrained shares (sum to 1).
    limits
        Per-option upper bounds.

    Returns
    -------
    tuple[FloatArray, str]
        Constrained shares and a warning message (empty when no warning).
    """
    limit_array = np.asarray(limits, dtype=np.float64)
    if limit_array.shape != shares.shape:
        raise ValueError(
            f"'limits' length ({limit_array.size}) must match 'values' length "
            f"({shares.size})"
        )

    limit_array = np.clip(limit_array, 0.0, 1.0)

    msg = ""

    # infeasible: even saturating every option cannot reach a unit total.
    total_limit = float(np.sum(limit_array))
    if total_limit < 1.0 - 1e-12:
        msg = (
            f"sum of limits ({total_limit:.4f}) is below 1; allocation is infeasible "
            "and every option has been saturated to its limit"
        )
        return limit_array.copy(), msg

    # no effective constraint.
    if not np.any(shares > limit_array + 1e-12):
        return shares.copy(), msg

    return _redistribute_proportional(shares, limit_array), msg


def _redistribute_proportional(shares: FloatArray, limits: FloatArray) -> FloatArray:
    """
    Clip shares exceeding their limit and rescale the rest so the total stays at 1.

    Each pass: shares above their limit are clipped and frozen; the non-saturated shares
    are multiplied by (1 - sum_clipped) / sum_free. Repeats up to `len(shares)` times
    since each pass freezes at least one new option. Applied to the uniform vector this
    is exactly water-filling.

    Parameters
    ----------
    shares
        Unconstrained shares (sum to 1).
    limits
        Per-option upper bounds.

    Returns
    -------
    FloatArray
        Constrained shares.
    """
    shares = np.array(shares, dtype=np.float64, copy=True)
    saturated = np.zeros_like(shares, dtype=bool)

    for _ in range(shares.size):
        over = (shares > limits + 1e-12) & ~saturated
        if not np.any(over):
            break

        shares[over] = limits[over]
        saturated |= over

        s_clip = float(np.sum(shares[saturated]))
        free_mask = ~saturated
        s_free = float(np.sum(shares[free_mask]))

        if s_free <= 0.0:
            break

        factor = (1.0 - s_clip) / s_free
        shares[free_mask] *= factor

    return shares


def calculate_two_axis_uptake[T: Hashable](
    group_keys: list[T],
    metrics_intra: list[float],
    metrics_inter: list[float],
    intra_utility: UtilityID,
    inter_utility: UtilityID,
    intra_odds: float,
    inter_odds: float,
    limits: FloatArray | None = None,
    context: str = "",
) -> FloatArray:
    """
    Calculate uptake shares using a two-axis discrete choice model.

    Assets are grouped by *group_keys* (e.g. fuel type). Within each group, intra-group
    shares are determined from *metrics_intra*. Across groups, inter-group shares are
    determined from each group's metric: its *metrics_inter* weighted by filling the
    group with its members in order of *metrics_intra*, best first, each up to its
    intra-group cap. Uncapped, this is the inter metric of the group's best member, so
    a group's metric does not fall when a worse option is added to it, nor rise when
    an identical one is. The final per-asset share is the product of the two.

    When *limits* is given, the per-asset bounds are projected onto the two axes: the
    inter-group cap is the sum of the member caps (clamped to 1.0), so a group can
    absorb its members' joint capacity, and the intra-group caps are normalized by the
    group cap so the composed bound ``group_cap * intra_cap`` equals the per-asset
    limit.

    Parameters
    ----------
    group_keys
        Grouping key per asset (e.g. fuel type name).
    metrics_intra
        Evaluation metric per asset for the intra-group axis.
    metrics_inter
        Evaluation metric per asset for the inter-group axis.
    intra_utility
        Utility transformation for the intra-group axis.
    inter_utility
        Utility transformation for the inter-group axis.
    intra_odds
        Odds ratio calibrating the intra-group sensitivity.
    inter_odds
        Odds ratio calibrating the inter-group sensitivity.
    limits
        Optional per-asset upper bound on the final share, each in [0, 1]. None disables
        limits.
    context
        Optional string used as prefix in warning messages.

    Returns
    -------
    FloatArray
        Uptake share per asset.
    """
    group_map = define_index_map(group_keys)

    uptake = np.zeros(len(group_keys))
    group_metrics: list[float] = []
    group_limits: list[float] = []

    for group, indices in group_map.items():
        intra = np.take(metrics_intra, indices)
        inter = np.take(metrics_inter, indices)

        if limits is None:
            intra_limits = np.ones(len(indices))
        else:
            group_cap = min(sum(limits[i] for i in indices), 1.0)
            group_limits.append(group_cap)
            if group_cap > 0.0:
                intra_limits = limits[indices] / group_cap
            else:
                # group hard-capped to zero by the inter-group limit; intra shares are
                # irrelevant but the intra DCM still needs well-posed limits
                intra_limits = np.ones(len(indices))

        shares, msg = calculate_asset_shares(
            intra, intra_utility, intra_odds, limits=intra_limits
        )
        metric = _calculate_group_metric(intra, inter, intra_limits, intra_utility)

        if msg:
            logger.warning("%s: intra-group '%s' %s", context, group, msg)

        uptake[indices] = shares
        group_metrics.append(metric)

    group_shares, msg = calculate_asset_shares(
        group_metrics,
        inter_utility,
        inter_odds,
        limits=group_limits if limits is not None else None,
    )

    if msg:
        logger.warning("%s: inter-group %s", context, msg)

    for indices, group_share in zip(group_map.values(), group_shares, strict=True):
        uptake[indices] *= group_share

    return uptake


def _calculate_group_metric(
    intra: FloatArray,
    inter: FloatArray,
    intra_limits: FloatArray,
    intra_utility: UtilityID,
) -> float:
    """
    Calculate a group's inter-group metric by filling the group with its best members.

    The members are ranked by their intra-group metric, best first, ties in input order,
    and each in turn fills the group up to its limit until the group is full. The
    group's metric is the inter-group metric weighted by that fill.

    Parameters
    ----------
    intra
        Intra-group metric per member, ranking the members.
    inter
        Inter-group metric per member.
    intra_limits
        Upper bound on each member's part of the group, each in [0, 1], summing to at
        least 1.
    intra_utility
        Utility transformation of the intra-group axis, saying whether lower or higher
        metrics are better.

    Returns
    -------
    float
        Inter-group metric of the group.
    """
    sign = 1.0 if intra_utility == UtilityID.LOWER_LOG_RATIO else -1.0
    ranking = np.argsort(sign * intra, kind="stable")

    filled = np.minimum(np.cumsum(intra_limits[ranking]), 1.0)
    fill = np.zeros_like(filled)
    fill[ranking] = np.diff(filled, prepend=0.0)

    return float(np.dot(inter, fill))
