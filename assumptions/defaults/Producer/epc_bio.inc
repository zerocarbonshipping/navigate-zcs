# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Producer "epc_bio" {
	Plants = [
	    Plant("plant_methane_bio_africa"),
	    Plant("plant_methane_bio_americas"),
	    Plant("plant_methane_bio_asia"),
	    Plant("plant_methane_bio_europe"),
	    Plant("plant_methane_bio_middle_east"),
	    Plant("plant_methanol_bio_smr_africa"),
	    Plant("plant_methanol_bio_smr_americas"),
	    Plant("plant_methanol_bio_smr_asia"),
	    Plant("plant_methanol_bio_smr_europe"),
	    Plant("plant_methanol_bio_smr_middle_east")
	]

	#InitialCapacity = [
	#    0,
    #    0,
    #    0,
    #    0,
    #    0,
    #    0,
    #    0,
    #    0,
    #    356, # 130 ktpa existing (BioMCN 60 + BASF 72 bio-share) = 356 t/d
    #    0
	#]

    MaximumDevelopment = Forecast("epc_bio_maximum_development")

    # feedstock availability
    set_feed_constraint("feedstock_biogas", <Forecast("feedstock_biogas_availability") * Forecast("feedstock_biogas_share_shipping")>)
}
