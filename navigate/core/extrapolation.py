# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The warning logged when a table look-up reaches beyond the tabulated range."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging

    from navigate.util import FloatArray


def log_extrapolate_bounds(
    logger: logging.Logger,
    node: object,
    lookup_values: FloatArray,
    lower: float,
    upper: float,
) -> None:
    """
    Warn that a table look-up reached beyond the tabulated range.

    Parameters
    ----------
    logger
        Logger to write to.
    node
        Node owning the table, named in the message.
    lookup_values
        Look-up values, reported when there are few enough to read.
    lower
        Lower limit of the tabulated range.
    upper
        Upper limit of the tabulated range.
    """
    # node is typed as object because the table mixins calling this are not
    # Node subclasses statically; it is only formatted into the message
    info = f" Value was {lookup_values}." if lookup_values.size < 5 else ""

    logger.warning(
        "%s: Extrapolating beyond table limits (%s, %s).%s", node, lower, upper, info
    )
