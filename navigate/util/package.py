# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The installed Navigate distribution: its name and version."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

DISTRIBUTION = "navigate-zcs"


def navigate_version() -> str | None:
    """
    Look up the version of the installed Navigate.

    Returns
    -------
    str | None
        The version, such as ``1.1.0`` or ``1.1.0.dev0``; None where Navigate
        runs from a source tree that is not installed.
    """
    try:
        return version(DISTRIBUTION)
    except PackageNotFoundError:
        return None
