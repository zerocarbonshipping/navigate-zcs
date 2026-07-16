# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Region "americas" {
    # sources ----------------------------------------------------------------------------------------------------------
    # source cost
    set_source_opex("renewable", Forecast("electricity_cost_americas_mid"))
    set_source_opex("grid", Forecast("electricity_cost_americas_mid"))    # renewable LCoE is used as a proxy as no alternative assumption is available

	# source emissions
	set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_americas"))
}