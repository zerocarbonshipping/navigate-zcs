# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Navigate's exception hierarchy, raised across the package and caught by the CLI."""

from __future__ import annotations


class NavigateError(Exception):
    """
    Base class for Navigate's domain-specific exceptions.

    Deck, command, attribute, and LP-solver errors raised anywhere in the
    package inherit from this common base so the top-level CLI handler in
    ``navigate.app.cli`` can catch them as one group and present a friendly
    message.
    """


class DeckError(NavigateError):
    """
    Raised for a mistake in the input deck the parser reads.

    The message names the deck line and the include file and line the mistake
    was written at, where the parser knows them.
    """


class DeckInsufficientError(NavigateError):
    """Raised if the deck contains insufficient information to run a simulation."""


class UnassignedAttributeError(DeckInsufficientError):
    """
    Raised if a node attribute the deck must assign is unassigned.

    Parameters
    ----------
    owner
        Display text of the node or general node whose attribute is unassigned.
    attribute_name
        Deck attribute left unassigned.
    """

    def __init__(self, owner: str, attribute_name: str) -> None:
        super().__init__(f"{owner}: Attribute '{attribute_name}' is unassigned.")


class InfeasibleLPError(NavigateError):
    """Raised if an LP is infeasible."""


class PowerCapacityError(NavigateError):
    """Raised if a vessel's energy demand exceeds installed converter power capacity."""


class ConvergenceError(NavigateError):
    """Raised if an iterative algorithm fails to converge."""
