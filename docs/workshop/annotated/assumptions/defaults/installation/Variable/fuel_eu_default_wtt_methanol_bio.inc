# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Default WTT emissions emitted per ton of bio-methanol under the FuelEU Maritime regulation.
# Unit: ton emission / ton fuel

Variable "fuel_eu_default_wtt_methanol_bio" {
    # Negative, as for any fuel made from biogenic carbon. That is not a
    # modelling shortcut: the regulation derives the WTT from the lifecycle
    # value on the fuel's Proof of Sustainability, reduced by the combustion
    # carbon.
    Value = -1.11
}
