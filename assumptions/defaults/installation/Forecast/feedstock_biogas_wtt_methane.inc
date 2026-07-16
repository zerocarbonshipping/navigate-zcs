# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Avoided methane emissions related to the use of biogas feedstock pool.
# ⚠️ REVIEW NEEDED — calibrated for pure waste; may overstate avoided emissions
#   for crop residues / energy crops in the blended pool.
# Unit: ton emissions / ton feedstock

Forecast "feedstock_biogas_wtt_methane" {
    Table = [
        "01-01-2025"    -0.00207
        "01-01-2050"    -0.00207
    ]
}
