# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from tanker_47k_dwt: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Converter "electrical_ice_methanol_chemical_tanker_40k_dwt" {
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = Variable("electrical_methanol_minimum_pilot_fuel")

	PowerCapacity = Variable("chemical_tanker_40k_dwt_electrical_power_capacity")
	Efficiency = Variable("electrical_methanol_efficiency")

	CAPEX = Forecast("electrical_methanol_capex")
	OPEX = Forecast("electrical_methanol_opex")
}
