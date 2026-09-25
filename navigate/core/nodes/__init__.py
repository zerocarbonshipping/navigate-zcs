# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The node classes a deck declares, one module per node type.

Deliberately empty as a matter of import hygiene: re-exports here would make
importing any one node class load all of them. Import concrete classes from
their own module, e.g. ``from navigate.core.nodes.vessel import Vessel``.
"""
