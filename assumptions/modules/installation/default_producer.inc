# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Import Producer "epc_global"
Import Producer "epc_bio"
Import Producer "epc_fame_europe"

# since all routes are regionalized and not reliant on a specific route,
# there is no difference between bunkering all fuels in a single port or
# in multiple ports. For simplicity all fuel is routed to "global".
# This way port_europe is only relevant for regulation purposes.
Producer "*" {
    set_export_distribution("port_global", 1.)
}
