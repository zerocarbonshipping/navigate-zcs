# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

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


def plot_engine_age(manager, directory):
    dateline = manager.dateline

    weighted_avg_age = manager.profile.get_weighted_average_age()

    # Filter out fuel types with no vessels (all-zero age)
    weighted_avg_age = {ft: age for ft, age in weighted_avg_age.items() if np.any(age > 0.)}

    if not weighted_avg_age:
        return

    fig, axes = subplot_grid(len(weighted_avg_age))

    y_max = max(np.nanmax(age) for age in weighted_avg_age.values())

    for ax, fuel_type in zip(axes, weighted_avg_age):
        age = weighted_avg_age[fuel_type]
        ax.plot(dateline, age, color=FUEL_TYPE_COLOR[fuel_type], lw=2.)
        ax.set_ylabel('Average age [years]')
        ax.set_title('{} vessels'.format(FUEL_TYPE_LABEL[fuel_type]))
        format_axes(ax, len(weighted_avg_age), dateline, legend=None)
        ax.set_ylim([0., y_max * 1.05])

    trim_axes(axes, len(weighted_avg_age))

    save_figure(fig, directory, 'engine_age.png')
