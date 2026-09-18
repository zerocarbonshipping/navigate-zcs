# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The parsed `Type("name")` token, as it stands before the node it names.

The parser materializes every token into its node when it reads the
assignment or command, so the only tokens that outlive that read are the ones
inside a queued EVENTS body, replayed at their date.
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
