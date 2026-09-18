# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The wildcard form of a DSL node reference.

It lives here, rather than beside the plain `Type("name")` token in the
parser, because `assign.py` must keep accepting it as an assigned value.
"""

from __future__ import annotations

from navigate.core.node_type import TypeCheckMixin


class WildcardNodeReference(TypeCheckMixin):
    """
    A node reference whose name contains glob wildcards (``*``, ``?``).

    Expanded into concrete nodes during reference resolution in the parser.
    May only appear inside list contexts; a ``WildcardNodeReference`` found
    outside a list raises an error.

    Parameters
    ----------
    type_
        Node type the pattern is matched within.
    name
        The glob pattern.
    """

    def __init__(self, type_: str, name: str) -> None:
        super().__init__(type_)

        self.name: str = name  # the glob pattern

    def __repr__(self) -> str:
        return f'{self.type}("{self.name}")'

    @property
    def pattern(self) -> str:
        """Return the glob the name is matched with."""
        return self.name
