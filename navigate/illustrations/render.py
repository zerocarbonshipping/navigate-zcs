# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import timeit

import matplotlib.pyplot as plt

from navigate.illustrations.plots._registry import PLOT_LABELS, PLOTS, plot_label
from navigate.illustrations.plots._style import initialize_matplotlib
from navigate.util import print_elapsed_time

logger = logging.getLogger(__name__)


def render_plots(manager, directory=None, selected_plots=None):
    initialize_matplotlib()
    start = timeit.default_timer()

    if directory is None:
        if hasattr(manager, '_parser'):
            deck_directory = manager._parser._deck_directory
        else:
            deck_directory = manager.get_deck_directory()
        directory = os.path.join(deck_directory, 'plots')

    os.makedirs(directory, exist_ok=True)

    dateline = manager._dateline

    if dateline.size < 2:
        return

    if selected_plots is not None:
        for label in selected_plots - PLOT_LABELS:
            logger.warning("Plot label '%s' was requested but does not exist.", label)

    plot_errors = 0

    for func in PLOTS:
        label = plot_label(func)
        if selected_plots is not None and label not in selected_plots:
            continue
        try:
            func(manager, directory)
        except Exception as e:
            plot_errors += 1
            logger.error("Plot '%s' failed: %s", label, e)
            plt.close('all')

    if plot_errors > 0:
        logger.warning("Plot generation completed with %d error(s).", plot_errors)

    print_elapsed_time(timeit.default_timer() - start, 'plots')
    logger.info('Plots generated successfully.')
