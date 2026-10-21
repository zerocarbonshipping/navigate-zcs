# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the global shore power share of the port energy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.output.plots._colors import SHORE_POWER_COLOR
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    single_panel,
)
from navigate.util import divide_nonzero, sum_values

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.output.simulation_results import SimulationResults


def plot_global_shore_power_share(results: SimulationResults, directory: Path) -> None:
    """Plot the global shore power share of the port energy."""
    dateline = results.dateline

    fig, ax = single_panel()

    global_results = results.global_results
    shore_power = global_results.shore_power_energy
    port_energy = sum_values(global_results.energy_port, dateline.shape)

    shore_power_share = divide_nonzero(shore_power, port_energy) * 100.0

    ax.fill_between(dateline, shore_power_share, color=SHORE_POWER_COLOR, alpha=0.6)
    ax.plot(dateline, shore_power_share, color=SHORE_POWER_COLOR, lw=2.5)

    ax.set_ylabel("Shore power share [%]")
    ax.set_ylim(bottom=0.0)
    format_axes(ax, 1, dateline)

    save_figure(fig, directory, "global_shore_power_share.png")
