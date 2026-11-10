# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The default library: which file in the assumptions folder holds a node or module.

Files sit at ``defaults/<NodeType>/<name>.inc`` and ``modules/<module>.inc``.
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import TYPE_CHECKING

from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from navigate.exceptions import DeckError
    from navigate.parser._syntax import SourceLocation

_DISTRIBUTION = "navigate-zcs"
_REPOSITORY = "https://github.com/zerocarbonshipping/navigate-zcs"


class Library:
    """The default library under ``data_dir``, or an empty one when it is None."""

    def __init__(self, data_dir: Path | None) -> None:
        self._root: Path | None = data_dir.resolve() if data_dir is not None else None

    def default_file(self, node_type: str, name: str) -> Path | None:
        """Return a default node's file, or None if the library has none."""
        return self._file("defaults", node_type, f"{name}.inc")

    def module_file(self, module: str) -> Path | None:
        """Return the file of a module named as a deck loads it, or None."""
        file_name = attribute_to_instance_name(module)
        return self._file("modules", f"{file_name}.inc")

    def missing_default_error(
        self, node_type: str, name: str, source: SourceLocation
    ) -> DeckError:
        """Build the error for a default node the library cannot supply."""
        if self._root is None:
            return _unavailable_error(f'Default {node_type}("{name}")', source)

        return source.error(
            f'{node_type}("{name}") is referenced but not found in either the deck '
            f"or the default location of {node_type}."
        )

    def missing_module_error(self, module: str, source: SourceLocation) -> DeckError:
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
    """
    Build the error for a request made with no assumptions folder given.

    It names the folder of the clone Navigate came from with the command that
    sets the environment variable on this system, or else links the download of
    the installed version's assumptions.
    """
    message = (
        f"{subject} is requested but no assumptions directory is specified. "
        "Specify it with the -d/--data-dir flag or the ASSUMPTIONS_DATA_DIR "
        "environment variable.\n"
    )

    folder = _clone_assumptions()
    if folder is not None:
        if sys.platform == "win32":
            command = f'setx ASSUMPTIONS_DATA_DIR "{folder}"'
        else:
            profile = "~/.zshrc" if sys.platform == "darwin" else "~/.bashrc"
            command = f"echo 'export ASSUMPTIONS_DATA_DIR=\"{folder}\"' >> {profile}"
        return source.error(
            f"{message}The assumptions are in {folder}. To use them in every run, "
            "set the environment variable once and open a new terminal:\n"
            f"    {command}\n"
            f'or pass the folder to this run with: -d "{folder}"'
        )

    try:
        version: str | None = distribution(_DISTRIBUTION).version
    except PackageNotFoundError:
        version = None

    # an unreleased version has no tag; the dev branch is where it comes from
    if version is None or ".dev" in version:
        what, ref = "the dev branch", "heads/dev"
    else:
        what, ref = f"Navigate {version}", f"tags/v{version}"

    return source.error(
        f"{message}Download the assumptions of {what}:\n"
        f"    {_REPOSITORY}/archive/refs/{ref}.zip\n"
        "unzip it and pass its assumptions folder with -d, or set "
        "ASSUMPTIONS_DATA_DIR to it."
    )


def _clone_assumptions() -> Path | None:
    """Return the assumptions folder of the clone Navigate came from, if any."""
    # an editable install runs from the clone, this file at <clone>/navigate/parser/;
    # 'pip install .' records the folder it installed from (PEP 610 'dir_info'),
    # where an install from a wheel or a git URL records no folder
    clones = [Path(__file__).resolve().parents[2]]
    try:
        record = distribution(_DISTRIBUTION).read_text("direct_url.json")
    except PackageNotFoundError:
        record = None

    direct_url = json.loads(record) if record else {}
    if "dir_info" in direct_url:
        clones.append(Path.from_uri(direct_url["url"]))

    return next(
        (
            clone / "assumptions"
            for clone in clones
            if (clone / "assumptions" / "defaults").is_dir()
        ),
        None,
    )
