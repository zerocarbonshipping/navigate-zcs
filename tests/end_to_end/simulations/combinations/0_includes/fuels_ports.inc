# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Two liquid-market fuels, so no supply chain has to be modelled. Every input
# an emission intensity derives from is pinned as a round constant: the fuels'
# heating values and TTW factors here, the upstream (WTT) factors at the ports,
# the methane slip in fleet.inc and the GWPs in model.inc. With them, per GJ
# of effective energy, (1 - slip) * LHV:
#
#   oil: WTT 0.8/40 = 20.0, TTW 3.2/40 = 80.0, WTW 100.0 kg CO2-eq/GJ
#   LNG: WTT 0.45/49.5 = 9.1, TTW (0.99*2.75 + 0.01*30)/49.5 = 61.1,
#        WTW 70.1 kg CO2-eq/GJ (slip 0.01, LHV 50, methane GWP 30)
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"

Fuel "fossil_fuel_oil" {
	LowerHeatingValue = 40.0                    # GJ/ton
	MassDensity = 0.9                           # ton/m3
	set_ttw("carbon_dioxide", 3.2)              # ton/ton fuel
}

Fuel "liquefied_natural_gas" {
	LowerHeatingValue = 50.0                    # GJ/ton
	MassDensity = 0.43                          # ton/m3
	set_ttw("carbon_dioxide", 2.75)             # ton/ton fuel
}

Import Port "port_global"
Import Port "port_europe"

Port "*" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", TRUE)

	set_bunker_price_overwrite("fossil_fuel_oil", 550)                   # USD/ton
	set_bunker_price_overwrite("liquefied_natural_gas", 380)             # USD/ton

	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", 0.8)   # ton/ton fuel
	set_bunker_wtt_overwrite("liquefied_natural_gas", "carbon_dioxide", 0.45)
}
