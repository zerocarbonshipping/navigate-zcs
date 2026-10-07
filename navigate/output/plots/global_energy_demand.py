# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the global energy demand by demand type."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import EnergyDemandTypeID
from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    format_axes,
    plot_stack_with_lines,
    save_figure,
    single_panel,
)
from navigate.output.plots._style import LEGEND_OPTIONS
from navigate.output.plots._units import get_best_unit_energy

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.simulation_results import SimulationResults


def plot_global_energy_demand(results: SimulationResults, directory: Path) -> None:
    """Plot the global energy demand by demand type."""
    dateline = results.dateline

    fig, ax = single_panel()

    profile = results.profile
    energy_sea = profile.get_energy_sea()
    energy_port = profile.get_energy_port()

    # in port, vessels demand electrical energy and heat only
    propulsion = energy_sea[EnergyDemandTypeID.PROPULSION]
    electrical = (
        energy_sea[EnergyDemandTypeID.ELECTRICAL]
        + energy_port[EnergyDemandTypeID.ELECTRICAL]
    )
    heat = energy_sea[EnergyDemandTypeID.HEAT] + energy_port[EnergyDemandTypeID.HEAT]

    divisor, unit = get_best_unit_energy(
        np.amax(propulsion + electrical + heat), unit_order=9
    )

    values = [propulsion / divisor, electrical / divisor, heat / divisor]
    labels = ["Propulsion", "Electrical", "Heat"]
    colors = [CENTER_COLORS_BLUE[3], CENTER_COLORS_GREEN[3], CENTER_COLORS_RED[3]]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel(f"Energy demand [{unit}]")
    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, "global_energy_demand.png")
