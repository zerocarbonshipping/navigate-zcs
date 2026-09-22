# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
from navigate.util import add_dicts


def plot_global_energy_demand(manager, directory):
    dateline = manager.dateline

    fig, ax = single_panel()

    profile = manager.profile
    energies = add_dicts(profile.get_energy_sea(), profile.get_energy_port())
    propulsion = energies[EnergyDemandTypeID.PROPULSION]
    electrical = energies[EnergyDemandTypeID.ELECTRICAL]
    heat = energies[EnergyDemandTypeID.HEAT]

    divisor, unit = get_best_unit_energy(
        np.amax(propulsion + electrical + heat), default=9
    )
    propulsion /= divisor
    electrical /= divisor
    heat /= divisor

    values = [propulsion, electrical, heat]
    labels = ["Propulsion", "Electrical", "Heat"]
    colors = [CENTER_COLORS_BLUE[3], CENTER_COLORS_GREEN[3], CENTER_COLORS_RED[3]]

    stack = plot_stack_with_lines(ax, dateline, values, labels, colors)

    ax.set_ylabel(f"Energy demand [{unit}]")
    legend = ax.legend(stack[::-1], labels[::-1], **LEGEND_OPTIONS)
    format_axes(ax, 1, dateline, legend)

    save_figure(fig, directory, "global_energy_demand.png")
