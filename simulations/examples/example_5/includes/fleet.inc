# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FLEET - Caribbean shipping in two groups.
#
#   reg_*   the regional fleet: domestic and intra-Caribbean ships, nearly all
#           under 5,000 GT. Counts from the IMO CARES report (2024), "Report on
#           Decarbonization of Domestic Shipping: Insights from Africa and the
#           Caribbean", p.19: 330 ships over 100 GT, 144 of them tugs and 47 ferries.
#   intl_*  the international ships that call at the region's hubs, all over
#           5,000 GT.
#
# Ship designs, costs, lifetimes, age profiles and trade growth are the library's
# own for each class. CARES finds no Caribbean domestic ship running on an
# alternative fuel, so every fleet starts on oil. The library's orderbooks are
# sized for the world fleet and are left out.
#
# NOT CALIBRATED, on purpose: with the library's world-average ships the
# regional fleet burns 419 kt of fuel in 2026, against 309 kt in CARES (+36 %).
# Caribbean ships are smaller (most CARES tugs are 250-300 GT).

# ---- regional: tugs (CARES: 144) -------------------------------------------
Copy Vessel "tug_ice_oil"      "reg_tug_oil"
Copy Vessel "tug_ice_methane"  "reg_tug_methane"
Copy Vessel "tug_ice_methanol" "reg_tug_methanol"
Copy Vessel "tug_ice_ammonia"  "reg_tug_ammonia"

Fleet "reg_tug" {
	Vessels = [Vessel("reg_tug_oil"), Vessel("reg_tug_methane"),
	           Vessel("reg_tug_methanol"), Vessel("reg_tug_ammonia")]
	InitialVessels = 144
	InitialSplit = [1.0, 0.0, 0.0, 0.0]
	InitialAgeDistribution = [Curve("age_dist_tug_oil"), 0, 0, 0]
	TradeGrowth = Forecast("trade_growth_tug")
	AllowSpeedManagement = FALSE
}

# ---- regional: ferries (CARES: 47) -----------------------------------------
# The library's ferry has no ammonia design.
Copy Vessel "ferry_ice_oil"      "reg_ferry_oil"
Copy Vessel "ferry_ice_methane"  "reg_ferry_methane"
Copy Vessel "ferry_ice_methanol" "reg_ferry_methanol"

Fleet "reg_ferry" {
	Vessels = [Vessel("reg_ferry_oil"), Vessel("reg_ferry_methane"),
	           Vessel("reg_ferry_methanol")]
	InitialVessels = 47
	InitialSplit = [1.0, 0.0, 0.0]
	InitialAgeDistribution = [Curve("age_dist_ferry_oil"), 0, 0]
	TradeGrowth = Forecast("trade_growth_ferry")
	AllowSpeedManagement = FALSE
}

# ---- regional: cargo and tankers (CARES: the other 139) --------------------
# CARES lists general cargo, product and chemical tankers, ro-ro, container ships
# and offshore supply vessels, but gives their counts only in a chart that could
# not be read. INVENTED: the 139 split as 85 general cargo ships and 54 small
# tankers, with the other types folded into these two.
Copy Vessel "general_cargo_ice_oil"      "reg_cargo_oil"
Copy Vessel "general_cargo_ice_methane"  "reg_cargo_methane"
Copy Vessel "general_cargo_ice_methanol" "reg_cargo_methanol"
Copy Vessel "general_cargo_ice_ammonia"  "reg_cargo_ammonia"

Fleet "reg_cargo" {
	Vessels = [Vessel("reg_cargo_oil"), Vessel("reg_cargo_methane"),
	           Vessel("reg_cargo_methanol"), Vessel("reg_cargo_ammonia")]
	InitialVessels = 85   # INVENTED split, see above
	InitialSplit = [1.0, 0.0, 0.0, 0.0]
	InitialAgeDistribution = [Curve("age_dist_general_cargo_oil"), 0, 0, 0]
	TradeGrowth = Forecast("trade_growth_general_cargo")
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.4
}

Copy Vessel "tanker_7500_dwt_ice_oil"      "reg_tanker_oil"
Copy Vessel "tanker_7500_dwt_ice_methane"  "reg_tanker_methane"
Copy Vessel "tanker_7500_dwt_ice_methanol" "reg_tanker_methanol"
Copy Vessel "tanker_7500_dwt_ice_ammonia"  "reg_tanker_ammonia"

Fleet "reg_tanker" {
	Vessels = [Vessel("reg_tanker_oil"), Vessel("reg_tanker_methane"),
	           Vessel("reg_tanker_methanol"), Vessel("reg_tanker_ammonia")]
	InitialVessels = 54   # INVENTED split, see above
	InitialSplit = [1.0, 0.0, 0.0, 0.0]
	InitialAgeDistribution = [Curve("age_dist_tanker_7500_dwt_oil"), 0, 0, 0]
	TradeGrowth = Forecast("trade_growth_tanker")
	set_fuel_conversion_cost("reg_tanker_oil", "reg_tanker_methanol", 9.4e6)
	set_fuel_conversion_cost("reg_tanker_oil", "reg_tanker_ammonia", 14e6)
	set_fuel_conversion_cost("reg_tanker_methane", "reg_tanker_ammonia", 16.7e6)
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.4
}

# ---- international: container feeders, US - Caribbean ---------------------
# Feeders in the region are 500-2,500 TEU (Caribbean Feeder Services: 13 ships of
# 500-1,700 TEU; Seaboard: 1,208-1,450 TEU; MundoMaritimo 2025-26), so the
# library's 1,500 TEU class. INVENTED: 40 ships.
Copy Vessel "container_1500_teu_ice_oil"      "intl_feeder_oil"
Copy Vessel "container_1500_teu_ice_methane"  "intl_feeder_methane"
Copy Vessel "container_1500_teu_ice_methanol" "intl_feeder_methanol"
Copy Vessel "container_1500_teu_ice_ammonia"  "intl_feeder_ammonia"

Fleet "intl_feeder" {
	Vessels = [Vessel("intl_feeder_oil"), Vessel("intl_feeder_methane"),
	           Vessel("intl_feeder_methanol"), Vessel("intl_feeder_ammonia")]
	InitialVessels = 40   # INVENTED
	InitialSplit = [1.0, 0.0, 0.0, 0.0]
	InitialAgeDistribution = [Curve("age_dist_container_1500_teu_oil"), 0, 0, 0]
	TradeGrowth = Forecast("trade_growth_container_1500_teu")
	set_fuel_conversion_cost("intl_feeder_oil", "intl_feeder_methanol", 10.3e6)
	set_fuel_conversion_cost("intl_feeder_oil", "intl_feeder_ammonia", 15.5e6)
	set_fuel_conversion_cost("intl_feeder_methane", "intl_feeder_ammonia", 17.5e6)
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.5
}
