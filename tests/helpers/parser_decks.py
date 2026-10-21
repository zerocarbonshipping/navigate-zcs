# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Deck snippets and a default-library builder shared by the parser unit tests.

FLEET is the smallest Fleet the parser reads without the shipped assumptions:
every node it references is declared, so no default is pulled. A Converter's
PowerCapacity is DEFINE-only and its Efficiency may change in EVENTS, which the
timeline and pinned-calculator tests rely on. Only a root node keeps what it
references alive through the unreachable-node prune, so a deck exercising a
non-root node hangs it under a top-level Emission (see `emission_holding`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

FLEET_TEMPLATE = """
Fleet "fleet" {{
    Vessels = [Vessel("vessel")]
    InterFuelSensitivity = 0.5
    IntraFuelSensitivity = 0.5
    InitialVessels = 100
}}
Vessel "vessel" {{
    PropulsionConverter = Converter("propulsion")
    ElectricalConverter = Converter("electrical")
    HeatConverter = Converter("heat")
    Route = Route("route")
    NominalCapacity = 8000
    Tanks = [Tank("tank")]
    PropulsionLoad = 10
}}
Converter "propulsion" {{
    PowerCapacity = {power_capacity}
    Efficiency = {efficiency}
    MainFuelTypes = OIL
}}
Converter "electrical" {{
    PowerCapacity = 10
    Efficiency = 0.5
    MainFuelTypes = OIL
}}
Copy Converter "electrical" "heat"
Tank "tank" {{
    FuelTypes = OIL
    Size = 9000
}}
Route "route" {{
    RouteType = TRAMP
    Ports = [Port("port")]
    TimeAtSea = 0.75
    set_voyage_distribution("*", "*", 1)
    set_speed("*", "*", 10)
}}
Port "port" {{ }}
"""

FUEL = """
Fuel "oil" {
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
}
"""


def fleet(power_capacity: str = "50", efficiency: str = "0.5") -> str:
    """Return the FLEET deck with the propulsion converter's two inputs."""
    return FLEET_TEMPLATE.format(power_capacity=power_capacity, efficiency=efficiency)


FLEET = fleet()


def variable(name: str = "v", **attributes: object) -> str:
    """Return a Variable declaration assigning the given attributes."""
    body = "".join(f"    {key} = {value}\n" for key, value in attributes.items())
    return f'Variable "{name}" {{\n{body}}}\n'


def emission_holding(reference: str, name: str = "e") -> str:
    """Return a root Emission whose GlobalWarmingPotential holds the reference."""
    return f'Emission "{name}" {{\n    GlobalWarmingPotential = {reference}\n}}\n'


def write_library(
    data_dir: Path, node_type: str, files: dict[str, str] | None = None
) -> Path:
    """
    Write a default library holding files of one node type.

    Parameters
    ----------
    data_dir
        Root of the assumptions tree to write.
    node_type
        The node type folder the files go in.
    files
        File stem to file content.

    Returns
    -------
    The assumptions root, ready to pass as the parser's data directory.
    """
    directory = data_dir / "defaults" / node_type
    directory.mkdir(parents=True, exist_ok=True)
    for stem, content in (files or {}).items():
        (directory / f"{stem}.inc").write_text(content)
    return data_dir


def line_of(path: Path, text: str) -> int:
    """Return the 1-based number of the first line of a file containing text."""
    lines = path.read_text().splitlines()
    return next(number for number, line in enumerate(lines, 1) if text in line)
