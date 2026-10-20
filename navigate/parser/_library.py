# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The default library: which file in the assumptions folder holds a node or module.

Files sit at ``defaults/<NodeType>/<name>.inc`` and ``modules/<module>.inc``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from navigate.exceptions import DeckError
    from navigate.parser._lark_parser import SourceLocation


class Library:
    """The default library under ``data_dir``, or an empty one when it is None."""

    def __init__(self, data_dir: Path | None) -> None:
        self._root: Path | None = Path(data_dir).resolve() if data_dir else None

    @property
    def available(self) -> bool:
        """Whether an assumptions folder was given."""
        return self._root is not None

    def unavailable_error(self, subject: str, source: SourceLocation) -> DeckError:
        """Build the error for a request made with no assumptions folder given."""
        return source.error(
            f"{subject} is requested but no assumptions directory is specified. "
            "Specify it with the -d/--data-dir flag or the ASSUMPTIONS_DATA_DIR "
            "environment variable."
        )

    def missing_default(
        self, node_type: str, name: str, source: SourceLocation
    ) -> DeckError:
        """
        Build the error for a default node the library cannot supply.

        Parameters
        ----------
        node_type
            The node type.
        name
            The node name.
        source
            Where the node is asked for.

        Returns
        -------
        DeckError
            Naming the missing assumptions folder where none was given, else
            the node and where it was looked for.
        """
        if self._root is None:
            return self.unavailable_error(f'Default {node_type}("{name}")', source)

        return source.error(
            f'{node_type}("{name}") is referenced but not found in either the deck '
            f"or the default location of {node_type}."
        )

    def default_file(self, node_type: str, name: str) -> Path | None:
        """Return a default node's file, or None if the library has none."""
        if self._root is None:
            return None

        path = self._root / "defaults" / node_type / f"{name}.inc"
        return path if path.is_file() else None

    def module_file(self, module: str) -> Path | None:
        """Return the file of a module named as a deck loads it, or None."""
        if self._root is None:
            return None

        path = self._root / "modules" / f"{attribute_to_instance_name(module)}.inc"
        return path if path.is_file() else None
