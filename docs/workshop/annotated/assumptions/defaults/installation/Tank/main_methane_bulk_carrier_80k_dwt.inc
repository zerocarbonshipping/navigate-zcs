# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The LNG tank of the dual-fuel LNG ship.
Tank "main_methane_bulk_carrier_80k_dwt" {
	FuelTypes = METHANE
	# 3,080 m3, the same Variable as the pilot-oil tank.
	Size = Variable("tank_size_bulk_carrier_80k_dwt")

	CAPEX = Forecast("tank_methane_capex_bulk_carrier_80k")
	# The yearly OPEX is 1 % of the CAPEX.
	OPEX = <Forecast("tank_methane_capex_bulk_carrier_80k") * Variable("tank_opex_percentage_of_capex")>
}
