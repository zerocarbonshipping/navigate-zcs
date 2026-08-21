# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Deliberately empty for the same reason as navigate/core/nodes/__init__.py:
# re-exporting the _GeneralNode subclasses here would recurse into
# navigate.core during its own initialization. Import classes from their own
# module, e.g. `from navigate.core.general_nodes.bunker_options import
# BunkerOptions`.
