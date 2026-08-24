# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plot-rendering package.

Each module defines one or more ``plot_<label>(manager, directory)`` functions.
The catalogue of which plots are rendered (and in what order) lives in
:mod:`navigate.output.plots._registry`; import plot functions from their
own modules rather than from this package.
"""
