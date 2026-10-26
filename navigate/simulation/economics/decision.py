# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Discrete choice: multinomial-logit asset shares and two-axis uptake."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
from scipy.optimize import brentq

from navigate.core.enum_ import UtilityID
from navigate.util import define_index_map

if TYPE_CHECKING:
    from collections.abc import Hashable

    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)

# slack on comparisons of shares with their limits, absorbing rounding error
_SHARE_TOLERANCE = 1e-12

# Brent's method on the group shares and their log scale: absolute tolerance 1e-12, and
# room for its worst case, about the square of bisection's 100 steps
_ROOT_OPTIONS = {"xtol": 1e-12, "maxiter": 100**2}


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
    values = np.asarray(values, dtype=np.float64)
    beta = _calculate_beta(odds, utility)

    if utility == UtilityID.LOWER_LOG_RATIO:
        shares, message = _calculate_shares_lower_log_ratio(values, beta)
    elif utility == UtilityID.HIGHER_LOG_RATIO:
        shares, message = _calculate_shares_higher_log_ratio(values, beta)
    else:
        shares, message = _calculate_shares_signed_reference(values, beta, reference)

    if limits is not None:
        limits = np.asarray(limits, dtype=np.float64)
        shares, limit_message = _calculate_limited_shares(shares, limits)
        if limit_message:
            message = f"{message}; {limit_message}" if message else limit_message

    return shares, message


def _calculate_beta(odds: float, utility: UtilityID) -> float:
    """
    Calculate the multinomial-logit sensitivity beta from an interpretable odds ratio.

    The DSL exposes only the odds ratio, stated for a reference change fixed per utility
    kind: a 10% higher metric for the log-ratio cases and an advantage equal to 5% of
    the reference value for the signed case. An odds ratio of 1 yields beta = 0
    (uniform shares); values on the wrong side of 1 yield beta < 0 (a perverse
    calibration).

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
    if utility == UtilityID.SIGNED_REFERENCE:
        return math.log(odds) / 0.05

    return _preference_sign(utility) * math.log(odds) / math.log(1.10)


def _preference_sign(utility: UtilityID) -> float:
    """
    Return 1 where a utility prefers higher metrics and -1 where it prefers lower ones.

    Parameters
    ----------
    utility
        Utility transformation.

    Returns
    -------
    float
        Sign of the preference.
    """
    return -1.0 if utility == UtilityID.LOWER_LOG_RATIO else 1.0


def _softmax(utilities: FloatArray) -> FloatArray:
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


def _calculate_shares_lower_log_ratio(
    values: FloatArray, beta: float
) -> tuple[FloatArray, str]:
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
        message = (
            "contains a non-positive value; the lower-is-better log-ratio utility is "
            "undefined, so shares were split uniformly among the alternatives at the "
            "minimum value"
        )
        return _uniform_at_min(values), message

    utilities = -beta * np.log(values / np.min(values))
    return _softmax(utilities), ""


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


def _calculate_shares_higher_log_ratio(
    values: FloatArray, beta: float
) -> tuple[FloatArray, str]:
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

    positive_values = values[positive]
    utilities = beta * np.log(positive_values / np.max(positive_values))
    shares[positive] = _softmax(utilities)

    return shares, ""


def _calculate_shares_signed_reference(
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
        message = "has a non-positive reference value; shares were split uniformly"
        return np.ones_like(values) / values.size, message

    return _softmax(beta * values / reference), ""


def _calculate_limited_shares(
    shares: FloatArray, limits: FloatArray
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
    if limits.shape != shares.shape:
        raise ValueError(
            f"'limits' length ({limits.size}) must match 'values' length "
            f"({shares.size})"
        )

    limits = np.clip(limits, 0.0, 1.0)

    # infeasible: even saturating every option cannot reach a unit total
    total_limit = float(np.sum(limits))
    if total_limit < 1.0 - _SHARE_TOLERANCE:
        message = (
            f"sum of limits ({total_limit:.4f}) is below 1; allocation is infeasible "
            "and every option has been saturated to its limit"
        )
        return limits, message

    # no effective constraint
    if not np.any(shares > limits + _SHARE_TOLERANCE):
        return shares, ""

    return _calculate_redistributed_shares(shares, limits), ""


def _calculate_redistributed_shares(
    shares: FloatArray, limits: FloatArray
) -> FloatArray:
    """
    Clip shares exceeding their limit and rescale the rest so the total stays at 1.

    Each pass: shares above their limit are clipped and frozen; the free shares are
    multiplied by (1 - saturated total) / free total. Repeats up to `len(shares)` times
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
    shares = shares.copy()
    saturated = np.zeros_like(shares, dtype=bool)

    for _ in range(shares.size):
        over = (shares > limits + _SHARE_TOLERANCE) & ~saturated
        if not np.any(over):
            break

        shares[over] = limits[over]
        saturated |= over

        free = ~saturated
        total_saturated = float(np.sum(shares[saturated]))
        total_free = float(np.sum(shares[free]))

        if total_free <= 0.0:
            break

        shares[free] *= (1.0 - total_saturated) / total_free

    return shares


class _Axis(NamedTuple):
    """One axis of the two-axis choice: a metric per asset, its utility and odds."""

    metrics: FloatArray
    utility: UtilityID
    odds: float

    def select(self, indices: list[int]) -> _Axis:
        """Restrict the axis to the assets at the indices."""
        return self._replace(metrics=self.metrics[indices])

    def calculate_shares(
        self, limits: FloatArray | None = None
    ) -> tuple[FloatArray, str]:
        """Calculate the assets' shares of the choice on this axis alone."""
        return calculate_asset_shares(
            self.metrics, self.utility, self.odds, limits=limits
        )

    def calculate_utility(self, metric: float) -> float:
        """Calculate the log-ratio utility of a metric, up to a constant per choice."""
        beta = _calculate_beta(self.odds, self.utility)
        return _preference_sign(self.utility) * beta * math.log(metric)


def calculate_two_axis_uptake[T: Hashable](
    group_keys: list[T],
    intra_metrics: list[float],
    inter_metrics: list[float],
    intra_utility: UtilityID,
    inter_utility: UtilityID,
    intra_odds: float,
    inter_odds: float,
    limits: FloatArray | None = None,
    context: str = "",
) -> FloatArray:
    """
    Calculate uptake shares using a two-axis discrete choice model.

    Assets are grouped by *group_keys* (e.g. fuel type). Across groups, inter-group
    shares are determined from each group's metric: its *inter_metrics* weighted by
    filling the group with its members in order of *intra_metrics*, best first. The
    fill only values the group; it allocates nothing. Without limits, it is the inter
    metric of the group's best member, so a group's metric does not fall when a worse
    option is added to it, nor rise when an identical one is. Within each group,
    intra-group shares are determined from *intra_metrics*. The final per-asset share
    is the product of the two.

    When *limits* is given and the unlimited choice exceeds any of them, member i of
    group g fills its group only up to ``c_i = min(1, L_i / (G_g * w_i))``, with
    ``L_i`` its limit, ``w_i`` its unlimited intra-group share and ``G_g`` the group's
    share. A group's metric then depends on its own share, and the group shares are
    solved as the fixed point at which each is the inter-group choice on those
    metrics, capped at ``min(sum(L_i), 1)``. Within the group, member i's share is
    bounded by ``L_i / G_g``. A member with ``c_i < 1`` thus ends exactly at its
    limit; one with ``c_i = 1`` is bounded by it only when a capped sibling's surplus
    would push it over. An unlimited choice within every limit is returned unchanged.

    Parameters
    ----------
    group_keys
        Grouping key per asset (e.g. fuel type name).
    intra_metrics
        Evaluation metric per asset for the intra-group axis.
    inter_metrics
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
    intra = _Axis(np.asarray(intra_metrics), intra_utility, intra_odds)
    inter = _Axis(np.asarray(inter_metrics), inter_utility, inter_odds)

    group_shares, inter_message = _calculate_group_shares(group_map, intra, inter)
    uptake, messages = _allocate_members(group_map, intra, group_shares, None)

    if limits is not None and np.any(uptake > limits):
        solved = _solve_group_shares(group_map, intra, inter, limits)
        group_shares, inter_message = solved
        uptake, messages = _allocate_members(group_map, intra, group_shares, limits)

    if inter_message:
        logger.warning("%s: inter-group %s", context, inter_message)

    for message in messages:
        logger.warning("%s: %s", context, message)

    return uptake


def _calculate_group_shares[T: Hashable](
    group_map: dict[T, list[int]], intra: _Axis, inter: _Axis
) -> tuple[FloatArray, str]:
    """
    Calculate each group's share from the inter-group choice on its unlimited metric.

    Parameters
    ----------
    group_map
        Indices of each group's assets.
    intra
        Intra-group axis.
    inter
        Inter-group axis.

    Returns
    -------
    tuple[FloatArray, str]
        Share of each group and a warning message (empty when no warning).
    """
    group_metrics = []

    for indices in group_map.values():
        group_intra = intra.select(indices)
        group_inter = inter.select(indices)
        fill_caps = np.ones(len(indices))

        metric = _calculate_group_metric(group_intra, group_inter, fill_caps)
        group_metrics.append(metric)

    return calculate_asset_shares(group_metrics, inter.utility, inter.odds)


def _calculate_group_metric(intra: _Axis, inter: _Axis, fill_caps: FloatArray) -> float:
    """
    Calculate a group's inter-group metric by filling the group with its best members.

    The members are ranked by their intra-group metric, best first, ties in input order,
    and each in turn fills the group up to its fill cap until the group is full. The
    group's metric is the inter-group metric weighted by that fill.

    Parameters
    ----------
    intra
        Intra-group axis of the group's members, ranking them.
    inter
        Inter-group axis of the group's members.
    fill_caps
        Upper bound on each member's part of the group, each in [0, 1], summing to at
        least 1: were every cap below 1, each limit would be below its wanted share,
        and the limits together below the group's share.

    Returns
    -------
    float
        Inter-group metric of the group.
    """
    preference = _preference_sign(intra.utility) * intra.metrics
    ranking = np.argsort(-preference, kind="stable")

    filled = np.minimum(np.cumsum(fill_caps[ranking]), 1.0)
    fill = np.zeros_like(filled)
    fill[ranking] = np.diff(filled, prepend=0.0)

    return float(np.dot(inter.metrics, fill))


def _allocate_members[T: Hashable](
    group_map: dict[T, list[int]],
    intra: _Axis,
    group_shares: FloatArray,
    limits: FloatArray | None,
) -> tuple[FloatArray, list[str]]:
    """
    Allocate each group's share among its members by the intra-group choice.

    Parameters
    ----------
    group_map
        Indices of each group's assets.
    intra
        Intra-group axis.
    group_shares
        Share of each group.
    limits
        Optional upper bound on each asset's final share, each in [0, 1].

    Returns
    -------
    tuple[FloatArray, list[str]]
        Uptake share per asset and the warning messages of the intra-group choices.
    """
    uptake = np.zeros(len(intra.metrics))
    messages = []

    for i, (group, indices) in enumerate(group_map.items()):
        group_share = group_shares[i]

        # a group without share gives its members none, whatever their bounds
        if limits is None or group_share == 0.0:
            bounds = None
        else:
            bounds = limits[indices] / group_share

        shares, message = intra.select(indices).calculate_shares(bounds)
        uptake[indices] = group_share * shares

        if message:
            messages.append(f"intra-group '{group}' {message}")

    return uptake, messages


def _solve_group_shares[T: Hashable](
    group_map: dict[T, list[int]],
    intra: _Axis,
    inter: _Axis,
    limits: FloatArray,
) -> tuple[FloatArray, str]:
    """
    Solve each group's share of the limited choice.

    With a log scale ``mu`` shared by all groups, group g takes

        ``G_g = min(C_g, exp(mu + V_g))``,

    where ``C_g = min(sum(L_i), 1)`` is its cap, ``V_g`` the log-ratio utility of its
    metric, and ``mu`` sets the shares' sum to 1. This is exactly the capped logit
    that `_calculate_limited_shares` and `_calculate_redistributed_shares` reach by
    redistribution. Under limits ``V_g`` depends on ``G_g`` through the fill caps, so
    each ``G_g`` is a root of its own equation, and ``mu`` a root of the shares' sum.

    When the members of every group rank alike on both axes, as vessel types do, a
    larger ``G_g`` lowers the fill caps and moves the fill to worse members, so ``V_g``
    does not rise with ``G_g``. Each group's equation then has one root in
    ``[0, C_g]``, and the sum of those roots does not fall with ``mu``, so ``mu`` is a
    single bracketed root as well. Where the members rank differently, a group's
    equation can have several roots, and the solved shares need not form a fixed point
    nor sum to 1.

    Only the log-ratio utilities are supported, so the inter-group metrics must be
    positive. Caps summing below 1 saturate every group, with the capped logit's
    warning.

    Parameters
    ----------
    group_map
        Indices of each group's assets.
    intra
        Intra-group axis.
    inter
        Inter-group axis.
    limits
        Upper bound on each asset's final share, each in [0, 1].

    Returns
    -------
    tuple[FloatArray, str]
        Share of each group and a warning message (empty when no warning).
    """
    groups = []
    for indices in group_map.values():
        groups.append(_LimitedGroup(indices, intra, inter, limits))

    # no group's utility exceeds that of its best member on the inter axis, so at the
    # lower scale the groups take at most half the total
    max_utilities = [group.max_utility for group in groups]
    lower = -float(np.logaddexp.reduce(max_utilities)) - math.log(2.0)

    # from the upper scale on, every group takes its cap
    cap_scales = []
    for group in groups:
        if group.cap > 0.0:
            cap_scales.append(math.log(group.cap) - group.calculate_utility(group.cap))
    upper = max(cap_scales, default=lower)

    if _calculate_total_excess(upper, groups) <= 0.0:
        log_scale = upper
    else:
        log_scale = brentq(
            _calculate_total_excess, lower, upper, args=(groups,), **_ROOT_OPTIONS
        )

    shares = np.array([group.calculate_share(log_scale) for group in groups])
    caps = np.array([group.cap for group in groups])

    return _calculate_limited_shares(shares, caps)


class _LimitedGroup:
    """A group of the limited choice, its utility depending on its own share."""

    def __init__(
        self, indices: list[int], intra: _Axis, inter: _Axis, limits: FloatArray
    ) -> None:
        group_intra = intra.select(indices)
        group_inter = inter.select(indices)
        intra_shares, _ = group_intra.calculate_shares()
        max_utility = max(map(group_inter.calculate_utility, group_inter.metrics))

        self.limits: FloatArray = limits[indices]
        self.intra: _Axis = group_intra
        self.inter: _Axis = group_inter
        self.intra_shares: FloatArray = intra_shares
        self.max_utility: float = max_utility
        self.cap: float = min(float(np.sum(self.limits)), 1.0)

    def calculate_fill_caps(self, share: float) -> FloatArray:
        """
        Calculate each member's fill cap at a share of the group.

        A member wanting more than its limit, ``share * w_i > L_i``, fills the part
        ``L_i / (share * w_i)`` of it; any other member fills in full.
        """
        wanted = share * self.intra_shares
        binding = wanted > self.limits

        return np.divide(self.limits, wanted, out=np.ones_like(wanted), where=binding)

    def calculate_utility(self, share: float) -> float:
        """Calculate the group's inter-group utility at a share of the group."""
        fill_caps = self.calculate_fill_caps(share)
        metric = _calculate_group_metric(self.intra, self.inter, fill_caps)

        return self.inter.calculate_utility(metric)

    def calculate_share(self, log_scale: float) -> float:
        """Calculate the group's share at a log scale, solving its own equation."""
        # a group without cap takes none, and one the logit gives its cap takes all
        if self.cap == 0.0 or self._calculate_excess(self.cap, log_scale) <= 0.0:
            return self.cap

        excess = self._calculate_excess
        root = brentq(excess, 0.0, self.cap, args=(log_scale,), **_ROOT_OPTIONS)

        return float(root)

    def _calculate_excess(self, share: float, log_scale: float) -> float:
        """Calculate how far a share exceeds the capped logit's share at its utility."""
        utility = self.calculate_utility(share)
        chosen = math.exp(min(math.log(self.cap), log_scale + utility))

        return share - chosen


def _calculate_total_excess(log_scale: float, groups: list[_LimitedGroup]) -> float:
    """
    Calculate how far the groups' shares at a log scale exceed a unit total.

    Parameters
    ----------
    log_scale
        Log scale shared by the groups' utilities.
    groups
        Groups of the limited choice.

    Returns
    -------
    float
        Total share of the groups minus 1.
    """
    shares = [group.calculate_share(log_scale) for group in groups]
    return sum(shares) - 1.0
