# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# The stock default container fleet ships all four fuel variants (ammonia,
# methane, methanol, oil) with domain-calibrated CAPEX/OPEX differentials —
# the very cost differences this deck exercises. A hand-rolled vessel set
# would substitute made-up cost gaps for the calibrated ones.
# Decision sensitivities come from Load DefaultCalibration in the .nav.
Import Fleet "container_15000_teu"
