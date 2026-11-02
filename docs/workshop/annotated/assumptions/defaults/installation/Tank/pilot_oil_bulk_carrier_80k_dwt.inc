# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# The oil tank of this class's dual-fuel ships (LNG, methanol and ammonia): the
# oil their engines need as pilot fuel.
Tank "pilot_oil_bulk_carrier_80k_dwt" {
	FuelTypes = OIL
	# 3,080 m3.
	Size = Variable("tank_size_bulk_carrier_80k_dwt")

	CAPEX = Forecast("tank_oil_capex")
	# The yearly OPEX is 1 % of the CAPEX.
	OPEX = <Forecast("tank_oil_capex") * Variable("tank_opex_percentage_of_capex")>
}
