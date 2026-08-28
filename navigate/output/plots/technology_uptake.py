# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

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
from navigate.output.plots._illu_util import (
    get_font_sizes,
    set_font_sizes,
    trim_axes,
)
from navigate.output.plots._style import (
    LEGEND_OPTIONS,
)
from navigate.util import extract_from_tuple_dict


def plot_technology_uptake(manager, directory):
    dateline = manager.dateline
    fleets = manager.nodes.fleets

    for fleet_name, fleet in fleets.items():

        profile = fleet.profile

        uptakes = profile.get_technology_uptake()
        uptakes_nb = profile.get_newbuild_technology_uptake()
        uptakes_rf = profile.get_retrofit_technology_uptake()

        if not uptakes and not uptakes_nb and not uptakes_rf:
            continue

        multipliers = profile.get_existing_vessels()

        uptake = {}
        uptake_nb = {}
        uptake_rf = {}

        technology_names = [technology.get_name() for technology in fleet.technologies]

        for name in technology_names:

            # NOTE: underlying storage is still a tuple-dict; keep extraction logic
            shares_nb = extract_from_tuple_dict(uptakes_nb, key2=name) if uptakes_nb else {}
            shares_rf = extract_from_tuple_dict(uptakes_rf, key2=name) if uptakes_rf else {}

            values_nb = [
                shares_nb[vessel.get_name()]
                for vessel in fleet.get_vessels()
                if vessel.get_name() in shares_nb
            ]
            values_rf = [
                shares_rf[vessel.get_name()]
                for vessel in fleet.get_vessels()
                if vessel.get_name() in shares_rf
            ]

            # the uptake tuple-dicts are dense over the same vessel set, so
            # filtering weights on shares_rf pairs them with values_rf
            weights = [
                multipliers[vessel.get_name()]
                for vessel in fleet.get_vessels()
                if vessel.get_name() in shares_rf
            ]
            weights_nb = [
                profile.get_newbuilds(vessel.get_name())
                for vessel in fleet.get_vessels()
                if vessel.get_name() in shares_nb
            ]

            # Fleet-wide weighted uptake (existing fleet)
            uptake[name] = profile.get_fleet_technology_uptake(name)

            # Newbuild uptake (weighted if weights exist; otherwise simple average)
            if values_nb:
                uptake_nb[name] = [
                    np.average([v[i] for v in values_nb], weights=[w[i] for w in weights_nb])
                    if (weights_nb and np.sum([w[i] for w in weights_nb]) > 0.0)
                    else np.average([v[i] for v in values_nb])
                    for i in range(dateline.size)
                ]
            else:
                uptake_nb[name] = [0.0 for _ in range(dateline.size)]

            # Yearly retrofit share — fleet-weighted by existing multipliers, since each per-vessel
            # entry is already `retrofit_count_v / multiplier_v` (a rate).
            if values_rf and weights:
                uptake_rf[name] = [
                    np.average([v[i] for v in values_rf], weights=[w[i] for w in weights])
                    if np.sum([w[i] for w in weights]) > 0.0 else 0.0
                    for i in range(dateline.size)
                ]
            else:
                uptake_rf[name] = [0.0 for _ in range(dateline.size)]

        # Nothing to plot?
        if not uptake:
            continue

        fig, axes = subplot_grid(len(uptake))

        fleet_color = CENTER_COLORS_RED[4]
        newbuild_color = CENTER_COLORS_GREEN[4]
        retrofit_color = CENTER_COLORS_BLUE[4]

        for ax, name in zip(axes, uptake):

            ax.plot(dateline, uptake[name], color=fleet_color, label="Fleet", lw=2)
            ax.plot(dateline[1:], uptake_nb[name][1:], color=newbuild_color, label="Newbuilds", lw=2)
            ax.plot(dateline[1:], uptake_rf[name][1:], color=retrofit_color, label="Retrofits", lw=2)

            ax.set_xlim([dateline[0], dateline[-1]])
            ax.set_ylim([0.0, 1.01])
            ax.set_ylabel("Uptake [-]")
            ax.set_title(name)
            ax.grid(True, lw=0.3, alpha=0.5)
            ax.legend(**LEGEND_OPTIONS)

            set_font_sizes(ax, *get_font_sizes(len(axes)))

        trim_axes(axes, len(uptake))

        save_figure(fig, directory, f"technology_uptake_{fleet_name}.png")
