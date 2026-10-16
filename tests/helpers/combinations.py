# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Deck assembly for the end-to-end combination tests.

A combination deck is a committed base, the includes in a deck family's
0_includes, plus any template includes from the family's directory, whose
%name% values are filled in per combination; with none, it is the base deck
itself. `write_combination` writes such a deck into a directory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

SIMULATIONS_DIR = Path(__file__).resolve().parents[1] / "end_to_end" / "simulations"

# the DSL's template value; a comment may name one without it being filled in
_TEMPLATE = re.compile(r"%[a-z_]+%")

type Layer = tuple[str, Mapping[str, object]]


@dataclass(frozen=True)
class DeckFamily:
    """
    A committed base deck and the template includes that vary it.

    Parameters
    ----------
    directory
        Holds the template includes, and the base in its 0_includes.
    define
        The base includes of the DEFINE section, in order, relative to the
        base or absolute.
    events
        The base include of the EVENTS section, relative to the base or
        absolute.
    """

    directory: Path
    define: tuple[str, ...]
    events: str

    @property
    def base(self) -> Path:
        """The directory of the base includes."""
        return self.directory / "0_includes"


COMBINATIONS = DeckFamily(
    SIMULATIONS_DIR / "combinations",
    ("model.inc", "fuels_ports.inc", "fleet.inc"),
    "timeline.inc",
)

# shares the model definition and the timeline of the combination decks
SUPPLY = DeckFamily(
    SIMULATIONS_DIR / "supply",
    (str(COMBINATIONS.base / "model.inc"), "fleet.inc", "supply_chain.inc"),
    str(COMBINATIONS.base / "timeline.inc"),
)


def fill_template(family: DeckFamily, name: str, values: Mapping[str, object]) -> str:
    """Return the template include `name` with each %key% replaced by its value."""
    text = (family.directory / name).read_text()
    for key, value in values.items():
        placeholder = f"%{key}%"
        assert placeholder in text, f"{name} has no {placeholder}"
        text = text.replace(placeholder, str(value))
    unfilled = [
        line for line in text.splitlines() if _TEMPLATE.search(line.split("#")[0])
    ]
    assert not unfilled, f"{name} has unfilled template values: {unfilled}"
    return text


def write_combination(deck_dir: Path, family: DeckFamily, *layers: Layer) -> None:
    """Write the family's base deck plus the given template layers into `deck_dir`."""
    define = [f'\tInclude "{family.base / name}"' for name in family.define]
    for name, values in layers:
        (deck_dir / name).write_text(fill_template(family, name, values))
        define.append(f'\tInclude "{name}"')

    (deck_dir / f"{deck_dir.name}.nav").write_text(
        "DEFINE {\n"
        + "\n".join(define)
        + "\n}\n\nEVENTS {\n"
        + f'\tInclude "{family.base / family.events}"\n'
        + "}\n"
    )
