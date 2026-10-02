# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot the fleet, newbuild and retrofit technology uptake, one figure per fleet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_RED,
)
from navigate.output.plots._figure import (
    save_figure,
    subplot_grid,
)
from navigate.output.plots._layout import (
    get_font_sizes,
    set_font_sizes,
    trim_axes,
)
from navigate.output.plots._style import LEGEND_OPTIONS

if TYPE_CHECKING:
    from navigate.output.plot_data import PlotData
    from navigate.util.types_ import FloatArray


def plot_technology_uptake(plot_data: PlotData, directory: str) -> None:
    """Plot the fleet, newbuild and retrofit technology uptake, one figure per fleet."""
    dateline = plot_data.dateline
    fleets = plot_data.nodes.fleets

    for fleet_name, fleet in fleets.items():
        profile = fleet.profile

        uptakes = profile.get_technology_uptake()
        uptakes_newbuild = profile.get_newbuild_technology_uptake()
        uptakes_retrofit = profile.get_retrofit_technology_uptake()

        if not uptakes and not uptakes_newbuild and not uptakes_retrofit:
            continue

        multipliers = profile.get_existing_vessels()
        newbuilds = profile.get_newbuilds()
        fleet_uptake = profile.get_fleet_technology_uptake()

        uptake: dict[str, FloatArray] = {}
        uptake_newbuild: dict[str, list[float]] = {}
        uptake_retrofit: dict[str, list[float]] = {}

        technology_names = [technology.name for technology in fleet.technologies]

        for name in technology_names:
            shares_newbuild = {
                vessel_name: share
                for (vessel_name, technology), share in uptakes_newbuild.items()
                if technology == name
            }
            shares_retrofit = {
                vessel_name: share
                for (vessel_name, technology), share in uptakes_retrofit.items()
                if technology == name
            }

            values_newbuild = [
                shares_newbuild[vessel.name]
                for vessel in fleet.vessels
                if vessel.name in shares_newbuild
            ]
            values_retrofit = [
                shares_retrofit[vessel.name]
                for vessel in fleet.vessels
                if vessel.name in shares_retrofit
            ]

            # the uptake tuple-dicts are dense over the same vessel set, so
            # filtering weights on shares_retrofit pairs them with values_retrofit
            weights_retrofit = [
                multipliers[vessel.name]
                for vessel in fleet.vessels
                if vessel.name in shares_retrofit
            ]
            weights_newbuild = [
                newbuilds[vessel.name]
                for vessel in fleet.vessels
                if vessel.name in shares_newbuild
            ]

            uptake[name] = fleet_uptake[name]

            # newbuild uptake is weighted by the newbuilds where there are any,
            # and a plain average otherwise
            if values_newbuild:
                uptake_newbuild[name] = [
                    np.average(
                        [value[step] for value in values_newbuild],
                        weights=[weight[step] for weight in weights_newbuild],
                    )
                    if (
                        weights_newbuild
                        and np.sum([weight[step] for weight in weights_newbuild]) > 0.0
                    )
                    else np.average([value[step] for value in values_newbuild])
                    for step in range(dateline.size)
                ]
            else:
                uptake_newbuild[name] = [0.0 for _ in range(dateline.size)]

            # the yearly retrofit share is weighted by the existing multipliers,
            # as each per-vessel entry is already a rate (retrofits per multiplier)
            if values_retrofit and weights_retrofit:
                uptake_retrofit[name] = [
                    np.average(
                        [value[step] for value in values_retrofit],
                        weights=[weight[step] for weight in weights_retrofit],
                    )
                    if np.sum([weight[step] for weight in weights_retrofit]) > 0.0
                    else 0.0
                    for step in range(dateline.size)
                ]
            else:
                uptake_retrofit[name] = [0.0 for _ in range(dateline.size)]

        if not uptake:
            continue

        fig, axes = subplot_grid(len(uptake))

        fleet_color = CENTER_COLORS_RED[4]
        newbuild_color = CENTER_COLORS_GREEN[4]
        retrofit_color = CENTER_COLORS_BLUE[4]

        for ax, name in zip(axes, uptake, strict=False):
            ax.plot(dateline, uptake[name], color=fleet_color, label="Fleet", lw=2)
            ax.plot(
                dateline[1:],
                uptake_newbuild[name][1:],
                color=newbuild_color,
                label="Newbuilds",
                lw=2,
            )
            ax.plot(
                dateline[1:],
                uptake_retrofit[name][1:],
                color=retrofit_color,
                label="Retrofits",
                lw=2,
            )

            ax.set_xlim(dateline[0], dateline[-1])
            ax.set_ylim(0.0, 1.01)
            ax.set_ylabel("Uptake [-]")
            ax.set_title(name)
            ax.grid(True, lw=0.3, alpha=0.5)
            ax.legend(**LEGEND_OPTIONS)

            set_font_sizes(ax, *get_font_sizes(len(axes)))

        trim_axes(axes, len(uptake))

        save_figure(fig, directory, f"technology_uptake_{fleet_name}.png")
