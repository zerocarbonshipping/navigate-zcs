# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# E-ammonia supply chain with every economic and sizing input pinned to an
# explicit constant (rounded from the 2026-08-13 installation defaults). The
# development headroom is deliberately ample: the levy, not the supply
# constraint, must shape the fuel choice.

# oil imports LiquidMarket = TRUE from the defaults: available without a
# Producer, priced and emission-rated at the ports
Import Fuel "fossil_fuel_oil"

Import Fuel "ammonia_electro"

Import Plant "plant_ammonia_electro_alkaline"

Plant "plant_ammonia_electro_alkaline" {
	Region = Region("europe")
	Source = Source("renewable")

	# pinned sizing
	Capacity = 1000      # ton/day
	LeadTime = 5         # years
	Lifetime = 30        # years
	Uptime = 0.9
}

Import Process "electrolysis_stack_alkaline"
Import Process "ammonia_synthesis_electro_alkaline"
Import Process "hydrogen_electro_alkaline"
Import Process "nitrogen_air_separation"
Import Feedstock "demineralized_water"

Producer "epc_europe" {
	Plants = [Plant("plant_ammonia_electro_alkaline")]

	# ample headroom (the supply-constrained guardrail decks use 1 and 8)
	MaximumDevelopment = 8

	# no artificial utilization ramp at simulation start
	JumpStartFraction = 1.0

	# pinned decision-process calibration (rounded from the 2026-09-14
	# installation defaults)
	Inertia = 0.0
	FuelDemandSensitivity = 1.25
	FuelCostSensitivity = 0.75

	set_export_distribution("port_global", 1.)
}

Import Source "renewable"

# pinned production economics (USD/ton unless noted)
Region "europe" {
	set_source_opex("renewable", 70)                # USD/MWh
	set_feedstock_cost("demineralized_water", 2)

	set_process_capex("electrolysis_stack_alkaline", 4000)
	set_process_opex("electrolysis_stack_alkaline", 160)
	set_process_energy("electrolysis_stack_alkaline", 51)    # MWh/ton
	set_process_lifetime("electrolysis_stack_alkaline", 10)  # years
	set_process_replacement("electrolysis_stack_alkaline", 0.2)

	set_process_capex("hydrogen_electro_alkaline", 3600)
	set_process_opex("hydrogen_electro_alkaline", 145)
	set_process_energy("hydrogen_electro_alkaline", 4.0)     # MWh/ton
	set_process_lifetime("hydrogen_electro_alkaline", 20)    # years
	set_process_replacement("hydrogen_electro_alkaline", 0.2)

	set_process_capex("ammonia_synthesis_electro_*", 900)
	set_process_opex("ammonia_synthesis_electro_*", 40)
	set_process_energy("ammonia_synthesis_electro_*", 0.44)  # MWh/ton
}
