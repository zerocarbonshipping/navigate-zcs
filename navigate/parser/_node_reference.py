# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The parsed `Type("name")` tokens, as they stand before the nodes they name.

`NodeReference` names one node, `WildcardNodeReference` a glob over the names
of a node type. The parser turns both into nodes when it reads the assignment
or command, so the only tokens that outlive that read are the ones inside a
queued EVENTS body, replayed at their date.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeReference:
    """A node named in a deck, by its node type and its name."""

    type: str
    name: str

    def __repr__(self) -> str:
        return f'{self.type}("{self.name}")'


@dataclass(frozen=True)
class WildcardNodeReference:
    """The nodes of one type whose names match a glob written in a deck."""

    type: str
    name: str

    def __repr__(self) -> str:
        return f'{self.type}("{self.name}")'
