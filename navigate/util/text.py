# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Text helpers for the messages Navigate logs."""

from __future__ import annotations

_HLINE = "=" * 120


def wrap_in_hlines(message: str) -> str:
    """
    Frame a message in horizontal lines.

    Parameters
    ----------
    message
        Message to frame.

    Returns
    -------
    str
        Framed message.
    """
    return "\n" + _HLINE + "\n" + message + "\n" + _HLINE + "\n"
