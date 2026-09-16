# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Navigate's exception hierarchy, raised across the package and caught by the CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from navigate.core.node import Node


class NavigateError(Exception):
    """
    Base class for Navigate's domain-specific exceptions.

    Deck, command, attribute, and LP-solver errors raised anywhere in the
    package inherit from this common base so the top-level CLI handler in
    ``navigate.__main__`` can catch them as one group and present a friendly
    message.

    Parameters
    ----------
    message
        Message presented by the top-level handler.
    """

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class DeckInsufficientError(NavigateError):
    """Raised if the deck contains insufficient information to run a simulation."""


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


class PlotDataError(NavigateError, ValueError):
    """
    Raised if --replot cannot find any plot configuration to render.

    Inherits from both NavigateError (so the top-level CLI handler catches it)
    and ValueError (so existing callers of replot() that handle ValueError
    keep working).
    """


def no_value_assigned_error(node: Node, attribute_name: str) -> NoReturn:
    """
    Raise a ValueError naming the node and its unassigned attribute.

    Parameters
    ----------
    node
        Node whose attribute is unassigned.
    attribute_name
        Name of the unassigned attribute.
    """
    raise ValueError(f"{node}: Attribute '{attribute_name}' is unassigned.")
