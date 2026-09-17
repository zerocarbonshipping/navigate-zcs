# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from navigate.core.node_type import TypeCheckMixin


class NodeReference(TypeCheckMixin):
    def __init__(self, type_: str, name: str) -> None:
        super().__init__(type_)

        self.name = name

    def __repr__(self):
        return f'{self.type}("{self.name}")'


class WildcardNodeReference(NodeReference):
    """
    A node reference whose name contains glob wildcards (``*``, ``?``).

    Expanded into concrete nodes during reference resolution in the parser.
    May only appear inside list contexts; a ``WildcardNodeReference`` found
    outside a list raises an error.
    """

    @property
    def pattern(self) -> str:
        return self.name
