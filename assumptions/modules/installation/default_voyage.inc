# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Import Route "operational_profile_bulk_carrier_26k_dwt"
Import Route "operational_profile_bulk_carrier_52k_dwt"
Import Route "operational_profile_bulk_carrier_80k_dwt"
Import Route "operational_profile_bulk_carrier_200k_dwt"

Import Route "operational_profile_container_1500_teu"
Import Route "operational_profile_container_4500_teu"
Import Route "operational_profile_container_8000_teu"
Import Route "operational_profile_container_15000_teu"

Import Route "operational_profile_cruise_25k_gt"
Import Route "operational_profile_cruise_100k_gt"
Import Route "operational_profile_cruise_175k_gt"

Import Route "operational_profile_ferry"

Import Route "operational_profile_gas_carrier_100k_cbm"

Import Route "operational_profile_general_cargo"

Import Route "operational_profile_offshore"

Import Route "operational_profile_other"

Import Route "operational_profile_roro_4000_ceu"
Import Route "operational_profile_roro_7000_ceu"

Import Route "operational_profile_tanker_7500_dwt"
Import Route "operational_profile_tanker_47k_dwt"
Import Route "operational_profile_tanker_127k_dwt"
Import Route "operational_profile_tanker_300k_dwt"

Import Route "operational_profile_tug"

Route "*" {

    set_voyage_distribution("*", "*", 0)

	# intra
	set_voyage_distribution("port_europe", "port_europe", Variable("voyage_international_europe_intra"))

	# Europe (incoming)
	set_voyage_distribution("port_global", "port_europe", Variable("voyage_international_europe_incoming"))

	# Europe (outgoing)
	set_voyage_distribution("port_europe", "port_global", Variable("voyage_international_europe_outgoing"))

	# remaining (intra + rest)
	set_voyage_distribution("port_global", "port_global", Variable("voyage_international_global"))
}
