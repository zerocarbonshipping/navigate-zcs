# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.util import define_index_map

logger = logging.getLogger(__name__)

# reference changes baked into the odds-ratio calibration. The log-ratio cases state the odds for a
# metric that is 10% higher; the signed case states the odds for an advantage equal to 5% of the
# reference value. The DSL exposes only the odds ratio; beta is derived from it here.
_REFERENCE_INCREASE = 0.10
_REFERENCE_ADVANTAGE = 0.05
_LOG_REFERENCE_INCREASE = np.log(1. + _REFERENCE_INCREASE)


def calculate_asset_shares(
    values: list | np.ndarray,
    utility: UtilityID,
    odds: float,
    reference: float | None = None,
    limits: list | np.ndarray | None = None,
) -> tuple[np.ndarray, str]:
    """
    Calculate the investment shares across alternatives from a case-specific dimensionless utility.

    Routes `values` through the `utility` transformation and returns softmax shares; `limits`, when
    given, caps shares and rescales the surplus proportionally.

    Parameters
    ----------
    values
        Metric per alternative (LCOT, LCoF, expected demand, or NPV depending on `utility`).
    utility
        Utility transformation to apply.
    odds
        Odds ratio calibrating the sensitivity (e.g. 0.5 = a 10% higher metric gets half the odds).
    reference
        Reference value for `SIGNED_REFERENCE` (e.g. ship CAPEX); ignored by the log-ratio utilities.
    limits
        Optional per-option upper bound on share, each in [0, 1]. If None, no constraint is applied.

    Returns
    -------
    Asset investment shares and a potential warning message.
    """

    beta = _beta_from_odds(odds, utility)

    if utility == UtilityID.LOWER_LOG_RATIO:
        shares, msg = _shares_lower_log_ratio(values, beta)
    elif utility == UtilityID.HIGHER_LOG_RATIO:
        shares, msg = _shares_higher_log_ratio(values, beta)
    else:
        shares, msg = _shares_signed_reference(values, beta, reference)

    if limits is not None:
        shares, limit_msg = _apply_limits(shares, limits)
        if limit_msg:
            msg = '{}; {}'.format(msg, limit_msg) if msg else limit_msg

    return shares, msg


def _beta_from_odds(odds: float, utility: UtilityID) -> float:
    """
    Convert an interpretable odds ratio into the multinomial-logit sensitivity beta.

    The reference change is fixed per utility kind: a 10% higher metric for the log-ratio cases and
    an advantage equal to 5% of the reference value for the signed case. An odds ratio of 1 yields
    beta = 0 (uniform shares); values on the wrong side of 1 yield beta < 0 (a perverse calibration).

    Parameters
    ----------
    odds
        Odds ratio (strictly positive; validated at the input level).
    utility
        Utility transformation the sensitivity is for.

    Returns
    -------
    Sensitivity coefficient beta.
    """

    if utility == UtilityID.LOWER_LOG_RATIO:
        return -np.log(odds) / _LOG_REFERENCE_INCREASE

    if utility == UtilityID.HIGHER_LOG_RATIO:
        return np.log(odds) / _LOG_REFERENCE_INCREASE

    return np.log(odds) / _REFERENCE_ADVANTAGE


def softmax(utilities: np.ndarray) -> np.ndarray:
    """
    Numerically stable softmax over deterministic utilities.

    Subtraction by the maximum value avoids exponential overflow while preserving the result.

    Parameters
    ----------
    utilities
        Deterministic utility per alternative.

    Returns
    -------
    Probability of choice per alternative.
    """

    utilities = np.asarray(utilities, dtype=np.float64)
    exp = np.exp(utilities - np.max(utilities))
    return exp / np.sum(exp)


def _shares_lower_log_ratio(values: list | np.ndarray, beta: float) -> tuple[np.ndarray, str]:
    """
    Shares for a lower-is-better metric via V_i = -beta * log(value_i / min_j value_j).

    The log form requires strictly positive values. If any value is non-positive the form is
    undefined, so shares are split uniformly among the alternatives tied at the minimum value.

    Parameters
    ----------
    values
        Strictly-positive metric per alternative (lower is better).
    beta
        Sensitivity coefficient.

    Returns
    -------
    Shares per alternative and a potential warning message.
    """

    values = np.asarray(values, dtype=np.float64)

    if np.any(values <= 0.):
        msg = ("contains a non-positive value; the lower-is-better log-ratio utility is undefined, "
               "so shares were split uniformly among the alternatives at the minimum value")
        return _uniform_at_min(values), msg

    utilities = -beta * np.log(values / np.min(values))
    return softmax(utilities), ''


def _shares_higher_log_ratio(values: list | np.ndarray, beta: float) -> tuple[np.ndarray, str]:
    """
    Shares for a higher-is-better metric via V_i = beta * log(value_i / max_j value_j).

    Alternatives with a value of zero receive zero share; the softmax is applied only to the
    strictly-positive alternatives. If every value is zero, all shares are zero (the caller is
    expected to short-circuit this case).

    Parameters
    ----------
    values
        Non-negative metric per alternative (higher is better, e.g. expected demand).
    beta
        Sensitivity coefficient.

    Returns
    -------
    Shares per alternative and a potential warning message.
    """

    values = np.asarray(values, dtype=np.float64)
    shares = np.zeros_like(values)

    positive = values > 0.
    if not np.any(positive):
        return shares, ''

    shares[positive] = softmax(beta * np.log(values[positive] / np.max(values[positive])))
    return shares, ''


def _shares_signed_reference(values: list | np.ndarray,
                             beta: float,
                             reference: float | None) -> tuple[np.ndarray, str]:
    """
    Shares for a signed metric scaled by a reference value via V_i = beta * value_i / reference.

    Handles positive, zero, or negative metrics (e.g. NPV). A non-positive reference makes the
    scaling undefined, so shares are split uniformly.

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
    Shares per alternative and a potential warning message.
    """

    values = np.asarray(values, dtype=np.float64)

    if (reference is None) or (reference <= 0.):
        msg = "has a non-positive reference value; shares were split uniformly"
        return np.ones_like(values) / values.size, msg

    return softmax(beta * values / reference), ''


def _uniform_at_min(values: np.ndarray) -> np.ndarray:
    """
    Assign uniform shares among the alternatives tied at the minimum value, zero elsewhere.

    Parameters
    ----------
    values
        Metric per alternative.

    Returns
    -------
    Shares per alternative.
    """

    shares = np.zeros_like(values)

    at_min = values == np.min(values)
    shares[at_min] = 1. / np.count_nonzero(at_min)

    return shares


def _apply_limits(shares: np.ndarray, limits: list | np.ndarray) -> tuple[np.ndarray, str]:
    """
    Enforce per-option upper bounds on a share vector, rescaling any surplus proportionally.

    Parameters
    ----------
    shares
        Unconstrained shares (sum to 1).
    limits
        Per-option upper bounds.

    Returns
    -------
    Constrained shares and a warning message (empty when no warning).
    """

    limits = np.asarray(limits, dtype=np.float64)
    if limits.shape != shares.shape:
        raise ValueError("'limits' length ({}) must match 'values' length ({})"
                         .format(limits.size, shares.size))

    limits = np.clip(limits, 0., 1.)

    msg = ''

    # infeasible: even saturating every option cannot reach a unit total.
    total_limit = float(np.sum(limits))
    if total_limit < 1. - 1e-12:
        msg = ("sum of limits ({:.4f}) is below 1; allocation is infeasible "
               "and every option has been saturated to its limit".format(total_limit))
        return limits.copy(), msg

    # no effective constraint.
    if not np.any(shares > limits + 1e-12):
        return shares.copy(), msg

    return _redistribute_proportional(shares, limits), msg


def _redistribute_proportional(shares: np.ndarray, limits: np.ndarray) -> np.ndarray:
    """
    Iteratively clip shares that exceed their limit and rescale the remaining shares so the total stays at 1.

    Each pass: shares above their limit are clipped and frozen; the non-saturated shares are multiplied by
    (1 - sum_clipped) / sum_free. Repeats up to `len(shares)` times since each pass freezes at least one
    new option. Applied to the uniform vector this is exactly water-filling.

    Parameters
    ----------
    shares
        Unconstrained shares (sum to 1).
    limits
        Per-option upper bounds.

    Returns
    -------
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

        if s_free <= 0.:
            break

        factor = (1. - s_clip) / s_free
        shares[free_mask] *= factor

    return shares


def calculate_two_axis_uptake(group_keys: list,
                              metrics_intra: list,
                              metrics_inter: list,
                              intra_utility: UtilityID,
                              inter_utility: UtilityID,
                              intra_odds: float,
                              inter_odds: float,
                              intra_limit: list | np.ndarray | None = None,
                              inter_limit: list | np.ndarray | None = None,
                              context: str = "") -> np.ndarray:
    """
    Calculate uptake shares using a two-axis discrete choice model.

    Assets are grouped by *group_keys* (e.g. fuel type). Within each group, intra-group shares are
    determined from *metrics_intra*. Across groups, inter-group shares are determined from the
    intra-share-weighted *metrics_inter*. The final per-asset share is the product of the two.

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
    intra_limit
        Optional per-asset share upper bounds for the intra-group axis.
    inter_limit
        Optional per-group share upper bounds for the inter-group axis.
    context
        Optional string used as prefix in warning messages.

    Returns
    -------
    Uptake share per asset.
    """

    group_map = define_index_map(group_keys)
    unique_groups = list(group_map.keys())
    metrics_inter_arr = np.asarray(metrics_inter, dtype=np.float64)

    metrics_2nd = []
    uptake = np.zeros((len(metrics_intra),))

    for group in unique_groups:

        indices = group_map[group]
        metrics_1st = [metrics_intra[i] for i in indices]
        shares, msg = calculate_asset_shares(metrics_1st, intra_utility, intra_odds, limits=intra_limit)

        if msg:
            logger.warning("%s: intra-group '%s' %s", context, group, msg)

        for i, share in zip(indices, shares):
            uptake[i] = share

        metrics_2nd.append(np.dot(metrics_inter_arr[indices], shares))

    group_shares, msg = calculate_asset_shares(metrics_2nd, inter_utility, inter_odds, limits=inter_limit)

    if msg:
        logger.warning("%s: inter-group %s", context, msg)

    for j, group in enumerate(unique_groups):
        indices = group_map[group]
        for i in indices:
            uptake[i] *= group_shares[j]

    return uptake
