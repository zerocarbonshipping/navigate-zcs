# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The default library: which file in the assumptions folder holds a node or module.

Files sit at ``defaults/<NodeType>/<name>.inc`` and ``modules/<module>.inc``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.exceptions import DeckError
    from navigate.parser._syntax import SourceLocation


class Library:
    """The default library under ``data_dir``, or an empty one when it is None."""

    def __init__(self, data_dir: Path | None) -> None:
        self._root = data_dir.resolve() if data_dir is not None else None

    def default_file(self, node_type: str, name: str) -> Path | None:
        """Return a default node's file, or None if the library has none."""
        return self._file("defaults", node_type, f"{name}.inc")

    def module_file(self, module: str) -> Path | None:
        """Return the file of a module named as a deck loads it, or None."""
        file_name = attribute_to_instance_name(module)
        return self._file("modules", f"{file_name}.inc")

    def missing_default(
        self, node_type: str, name: str, source: SourceLocation
    ) -> DeckError:
        """Build the error for a default node the library cannot supply."""
        if self._root is None:
            return _unavailable_error(f'Default {node_type}("{name}")', source)

        return source.error(
            f'{node_type}("{name}") is referenced but not found in either the deck '
            f"or the default location of {node_type}."
        )

    def missing_module(self, module: str, source: SourceLocation) -> DeckError:
        """Build the error for a module the library cannot supply."""
        if self._root is None:
            return _unavailable_error(f"Module '{module}'", source)

        return source.error(f"No module with name '{module}' was found.")

    def _file(self, *parts: str) -> Path | None:
        if self._root is None:
            return None

        path = self._root.joinpath(*parts)
        return path if path.is_file() else None


def _unavailable_error(subject: str, source: SourceLocation) -> DeckError:
    """Build the error for a request made with no assumptions folder given."""
    return source.error(
        f"{subject} is requested but no assumptions directory is specified. "
        "Specify it with the -d/--data-dir flag or the ASSUMPTIONS_DATA_DIR "
        "environment variable."
    )
