# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Navigate's exception hierarchy, raised across the package and caught by the CLI."""

from __future__ import annotations


class NavigateError(Exception):
    """
    Base class for Navigate's domain-specific exceptions.

    Deck, command, attribute, and LP-solver errors raised anywhere in the
    package inherit from this common base so the top-level CLI handler in
    ``navigate.__main__`` can catch them as one group and present a friendly
    message.
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


class DeckFormatError(NavigateError):
    """Raised if there is a formatting error in the input deck read by the Parser."""


class DeckKeywordError(NavigateError):
    """Raised if there is a keyword error in the input deck read by the Parser."""


class AttributeAssignmentError(NavigateError):
    """Raised if there is an assignment error in the input deck read by the Parser."""


class CommandError(NavigateError):
    """Raised if there is a command error in the input deck read by the Parser."""


class InfeasibleLPError(NavigateError):
    """Raised if an LP is infeasible."""


class PowerCapacityError(NavigateError):
    """Raised if a vessel's energy demand exceeds installed converter power capacity."""


class ConvergenceError(NavigateError):
    """Raised if an iterative algorithm fails to converge."""
