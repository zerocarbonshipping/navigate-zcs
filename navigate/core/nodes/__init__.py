# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Deliberately empty: this package holds the Node subclasses, which import
# from navigate.core (Scalar, assign_*, ...). navigate.core.assign imports
# Node for an isinstance check, so if this __init__ re-exported any
# concrete class, importing navigate.core would recurse back into
# navigate.core before it finishes initializing. Import concrete classes
# from their own module, e.g. `from navigate.core.nodes.vessel import Vessel`.
