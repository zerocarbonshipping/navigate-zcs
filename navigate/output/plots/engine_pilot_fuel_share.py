# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots._figure import (
    format_axes,
    save_figure,
    subplot_grid,
)
from navigate.output.plots._illu_util import (
    trim_axes,
)
from navigate.output.plots._labels import (
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
)


def plot_engine_pilot_fuel_share(manager, directory):
    dateline = manager.get_dateline()
    converters = manager.nodes.converters

    relevant_fuel_types = [FuelTypeID.METHANE, FuelTypeID.METHANOL, FuelTypeID.AMMONIA]

    pilot_fuel_share = {fuel_type: manager.profile.get_pilot_fuel_share(fuel_type)
                        for fuel_type in relevant_fuel_types}
    pilot_fuel_share = {fuel_type: np.where(pilot_fuel_share[fuel_type]
                                            > 0., pilot_fuel_share[fuel_type], np.nan)
                        for fuel_type in relevant_fuel_types}

    # find minimum pilot fuel. Assuming it is constant and similar for all converters. Too simplistic.
    minimum_share = {fuel_type: 0. for fuel_type in pilot_fuel_share}

    for converter in converters.values():

        # assume single main fuel
        main_fuel_type = converter.main_fuel_types[0]

        if main_fuel_type in relevant_fuel_types:

            # assume share is constant
            min_share = converter.minimum_pilot_fuel.get()
            minimum_share[main_fuel_type] = max(minimum_share[main_fuel_type], min_share)

    fig, axes = subplot_grid(len(pilot_fuel_share))

    for ax, fuel_type in zip(axes, relevant_fuel_types):

        share = pilot_fuel_share[fuel_type] * 100.
        minimum = np.full_like(dateline, minimum_share[fuel_type] * 100., dtype=np.float64)

        ax.plot(dateline, share, color=FUEL_TYPE_COLOR[fuel_type], label='Actual share', lw=2.5)
        ax.plot(dateline, minimum, color='k', ls='--', label='Minimum share', lw=1.5)

        ax.set_ylabel('Pilot fuel share [%]')
        ax.set_title('{} vessels'.format(FUEL_TYPE_LABEL[fuel_type]))
        legend = ax.legend()
        format_axes(ax, len(pilot_fuel_share), dateline, legend)

    for ax in axes:
        ax.set_ylim([0., 100.])

    trim_axes(axes, len(pilot_fuel_share))

    save_figure(fig, directory, 'engine_pilot_fuel_share.png')
