# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Copy Fleet "bulk_carrier_26k_dwt" 	"bulk_carrier_26k_dwt_international"
Copy Fleet "bulk_carrier_52k_dwt" 	"bulk_carrier_52k_dwt_international"
Copy Fleet "bulk_carrier_80k_dwt" 	"bulk_carrier_80k_dwt_international"
Copy Fleet "bulk_carrier_200k_dwt" 	"bulk_carrier_200k_dwt_international"

Copy Fleet "container_1500_teu" 	"container_1500_teu_international"
Copy Fleet "container_4500_teu" 	"container_4500_teu_international"
Copy Fleet "container_8000_teu" 	"container_8000_teu_international"
Copy Fleet "container_15000_teu" 	"container_15000_teu_international"

Copy Fleet "cruise_25k_gt" 			"cruise_25k_gt_international"
Copy Fleet "cruise_100k_gt" 		"cruise_100k_gt_international"
Copy Fleet "cruise_175k_gt" 		"cruise_175k_gt_international"

Copy Fleet "ferry" 					"ferry_international"

Copy Fleet "gas_carrier_100k_cbm" 	"gas_carrier_100k_cbm_international"

Copy Fleet "general_cargo" 			"general_cargo_international"

Copy Fleet "offshore" 				"offshore_international"

Copy Fleet "other" 					"other_international"

Copy Fleet "roro_4000_ceu" 			"roro_4000_ceu_international"
Copy Fleet "roro_7000_ceu" 			"roro_7000_ceu_international"

Copy Fleet "tanker_7500_dwt" 		"tanker_7500_dwt_international"
Copy Fleet "tanker_47k_dwt" 		"tanker_47k_dwt_international"
Copy Fleet "tanker_127k_dwt" 		"tanker_127k_dwt_international"
Copy Fleet "tanker_300k_dwt" 		"tanker_300k_dwt_international"

Copy Fleet "tug" 					"tug_international"

# -------------------------------- bulk_carrier_26k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_26k_dwt_ice_ammonia" 	    "bulk_carrier_26k_dwt_ice_ammonia_international"
Copy Vessel "bulk_carrier_26k_dwt_ice_methane" 	"bulk_carrier_26k_dwt_ice_methane_international"
Copy Vessel "bulk_carrier_26k_dwt_ice_methanol" 	"bulk_carrier_26k_dwt_ice_methanol_international"
Copy Vessel "bulk_carrier_26k_dwt_ice_oil" 		    "bulk_carrier_26k_dwt_ice_oil_international"

Copy Route "operational_profile_bulk_carrier_26k_dwt"   "operational_profile_bulk_carrier_26k_dwt_international"

Vessel "bulk_carrier_26k_dwt_*_international" {
	Route = Route("operational_profile_bulk_carrier_26k_dwt_international")
}

Fleet "bulk_carrier_26k_dwt_international" {

	Vessels = [
		Vessel("bulk_carrier_26k_dwt_ice_ammonia_international"),
		Vessel("bulk_carrier_26k_dwt_ice_methane_international"),
		Vessel("bulk_carrier_26k_dwt_ice_methanol_international"),
	    Vessel("bulk_carrier_26k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_26k_dwt") * Variable("bulk_carrier_26k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_26k_dwt_ammonia") *    Variable("bulk_carrier_26k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_26k_dwt_methane") * Variable("bulk_carrier_26k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_26k_dwt_methanol") *   Variable("bulk_carrier_26k_dwt_international_share")>,
	    <Forecast("orderbook_bulk_carrier_26k_dwt_oil") *        Variable("bulk_carrier_26k_dwt_international_share")>
	]
}

# -------------------------------- bulk_carrier_52k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_52k_dwt_ice_ammonia" 	    "bulk_carrier_52k_dwt_ice_ammonia_international"
Copy Vessel "bulk_carrier_52k_dwt_ice_methane" 	"bulk_carrier_52k_dwt_ice_methane_international"
Copy Vessel "bulk_carrier_52k_dwt_ice_methanol" 	"bulk_carrier_52k_dwt_ice_methanol_international"
Copy Vessel "bulk_carrier_52k_dwt_ice_oil" 		    "bulk_carrier_52k_dwt_ice_oil_international"

Copy Route "operational_profile_bulk_carrier_52k_dwt"   "operational_profile_bulk_carrier_52k_dwt_international"

Vessel "bulk_carrier_52k_dwt_*_international" {
	Route = Route("operational_profile_bulk_carrier_52k_dwt_international")
}

Fleet "bulk_carrier_52k_dwt_international" {

	Vessels = [
		Vessel("bulk_carrier_52k_dwt_ice_ammonia_international"),
		Vessel("bulk_carrier_52k_dwt_ice_methane_international"),
		Vessel("bulk_carrier_52k_dwt_ice_methanol_international"),
	    Vessel("bulk_carrier_52k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_52k_dwt") * Variable("bulk_carrier_52k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_52k_dwt_ammonia") *    Variable("bulk_carrier_52k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_52k_dwt_methane") * Variable("bulk_carrier_52k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_52k_dwt_methanol") *   Variable("bulk_carrier_52k_dwt_international_share")>,
	    <Forecast("orderbook_bulk_carrier_52k_dwt_oil") *        Variable("bulk_carrier_52k_dwt_international_share")>
	]
}


# -------------------------------- bulk_carrier_80k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_80k_dwt_ice_ammonia" 	    "bulk_carrier_80k_dwt_ice_ammonia_international"
Copy Vessel "bulk_carrier_80k_dwt_ice_methane" 	"bulk_carrier_80k_dwt_ice_methane_international"
Copy Vessel "bulk_carrier_80k_dwt_ice_methanol" 	"bulk_carrier_80k_dwt_ice_methanol_international"
Copy Vessel "bulk_carrier_80k_dwt_ice_oil" 		    "bulk_carrier_80k_dwt_ice_oil_international"

Copy Route "operational_profile_bulk_carrier_80k_dwt"   "operational_profile_bulk_carrier_80k_dwt_international"

Vessel "bulk_carrier_80k_dwt_*_international" {
	Route = Route("operational_profile_bulk_carrier_80k_dwt_international")
}

Fleet "bulk_carrier_80k_dwt_international" {

	Vessels = [
		Vessel("bulk_carrier_80k_dwt_ice_ammonia_international"),
		Vessel("bulk_carrier_80k_dwt_ice_methane_international"),
		Vessel("bulk_carrier_80k_dwt_ice_methanol_international"),
	    Vessel("bulk_carrier_80k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_80k_dwt") * Variable("bulk_carrier_80k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_80k_dwt_ammonia") *    Variable("bulk_carrier_80k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_80k_dwt_methane") * Variable("bulk_carrier_80k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_80k_dwt_methanol") *   Variable("bulk_carrier_80k_dwt_international_share")>,
	    <Forecast("orderbook_bulk_carrier_80k_dwt_oil") *        Variable("bulk_carrier_80k_dwt_international_share")>
	]
}

# -------------------------------- bulk_carrier_200k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_200k_dwt_ice_ammonia" 	  "bulk_carrier_200k_dwt_ice_ammonia_international"
Copy Vessel "bulk_carrier_200k_dwt_ice_methane"   "bulk_carrier_200k_dwt_ice_methane_international"
Copy Vessel "bulk_carrier_200k_dwt_ice_methanol" 	  "bulk_carrier_200k_dwt_ice_methanol_international"
Copy Vessel "bulk_carrier_200k_dwt_ice_oil" 		  "bulk_carrier_200k_dwt_ice_oil_international"

Copy Route "operational_profile_bulk_carrier_200k_dwt"   "operational_profile_bulk_carrier_200k_dwt_international"

Vessel "bulk_carrier_200k_dwt_*_international" {
	Route = Route("operational_profile_bulk_carrier_200k_dwt_international")
}

Fleet "bulk_carrier_200k_dwt_international" {

	Vessels = [
		Vessel("bulk_carrier_200k_dwt_ice_ammonia_international"),
		Vessel("bulk_carrier_200k_dwt_ice_methane_international"),
		Vessel("bulk_carrier_200k_dwt_ice_methanol_international"),
	    Vessel("bulk_carrier_200k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_200k_dwt") * Variable("bulk_carrier_200k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_200k_dwt_ammonia") *    Variable("bulk_carrier_200k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_200k_dwt_methane") * Variable("bulk_carrier_200k_dwt_international_share")>,
		<Forecast("orderbook_bulk_carrier_200k_dwt_methanol") *   Variable("bulk_carrier_200k_dwt_international_share")>,
	    <Forecast("orderbook_bulk_carrier_200k_dwt_oil") *        Variable("bulk_carrier_200k_dwt_international_share")>
	]
}

# -------------------------------- container_1500_teu -------------------------------- #

Copy Vessel "container_1500_teu_ice_ammonia" 	    "container_1500_teu_ice_ammonia_international"
Copy Vessel "container_1500_teu_ice_methane" 	"container_1500_teu_ice_methane_international"
Copy Vessel "container_1500_teu_ice_methanol" 	    "container_1500_teu_ice_methanol_international"
Copy Vessel "container_1500_teu_ice_oil" 		    "container_1500_teu_ice_oil_international"

Copy Route "operational_profile_container_1500_teu"   "operational_profile_container_1500_teu_international"

Vessel "container_1500_teu_*_international" {
	Route = Route("operational_profile_container_1500_teu_international")
}

Fleet "container_1500_teu_international" {

	Vessels = [
		Vessel("container_1500_teu_ice_ammonia_international"),
		Vessel("container_1500_teu_ice_methane_international"),
		Vessel("container_1500_teu_ice_methanol_international"),
	    Vessel("container_1500_teu_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_container_1500_teu") * Variable("container_1500_teu_international_share")>

	Orderbooks = [
		<Forecast("orderbook_container_1500_teu_ammonia") *    Variable("container_1500_teu_international_share")>,
		<Forecast("orderbook_container_1500_teu_methane") * Variable("container_1500_teu_international_share")>,
		<Forecast("orderbook_container_1500_teu_methanol") *   Variable("container_1500_teu_international_share")>,
	    <Forecast("orderbook_container_1500_teu_oil") *        Variable("container_1500_teu_international_share")>
	]
}

# -------------------------------- container_4500_teu -------------------------------- #

Copy Vessel "container_4500_teu_ice_ammonia" 	    "container_4500_teu_ice_ammonia_international"
Copy Vessel "container_4500_teu_ice_methane" 	"container_4500_teu_ice_methane_international"
Copy Vessel "container_4500_teu_ice_methanol" 	    "container_4500_teu_ice_methanol_international"
Copy Vessel "container_4500_teu_ice_oil" 		    "container_4500_teu_ice_oil_international"

Copy Route "operational_profile_container_4500_teu"   "operational_profile_container_4500_teu_international"

Vessel "container_4500_teu_*_international" {
	Route = Route("operational_profile_container_4500_teu_international")
}

Fleet "container_4500_teu_international" {

	Vessels = [
		Vessel("container_4500_teu_ice_ammonia_international"),
		Vessel("container_4500_teu_ice_methane_international"),
		Vessel("container_4500_teu_ice_methanol_international"),
	    Vessel("container_4500_teu_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_container_4500_teu") * Variable("container_4500_teu_international_share")>

	Orderbooks = [
		<Forecast("orderbook_container_4500_teu_ammonia") *    Variable("container_4500_teu_international_share")>,
		<Forecast("orderbook_container_4500_teu_methane") * Variable("container_4500_teu_international_share")>,
		<Forecast("orderbook_container_4500_teu_methanol") *   Variable("container_4500_teu_international_share")>,
	    <Forecast("orderbook_container_4500_teu_oil") *        Variable("container_4500_teu_international_share")>
	]
}

# -------------------------------- container_8000_teu -------------------------------- #

Copy Vessel "container_8000_teu_ice_ammonia" 	    "container_8000_teu_ice_ammonia_international"
Copy Vessel "container_8000_teu_ice_methane" 	"container_8000_teu_ice_methane_international"
Copy Vessel "container_8000_teu_ice_methanol" 	    "container_8000_teu_ice_methanol_international"
Copy Vessel "container_8000_teu_ice_oil" 		    "container_8000_teu_ice_oil_international"

Copy Route "operational_profile_container_8000_teu"   "operational_profile_container_8000_teu_international"

Vessel "container_8000_teu_*_international" {
	Route = Route("operational_profile_container_8000_teu_international")
}

Fleet "container_8000_teu_international" {

	Vessels = [
		Vessel("container_8000_teu_ice_ammonia_international"),
		Vessel("container_8000_teu_ice_methane_international"),
		Vessel("container_8000_teu_ice_methanol_international"),
	    Vessel("container_8000_teu_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_container_8000_teu") * Variable("container_8000_teu_international_share")>

	Orderbooks = [
		<Forecast("orderbook_container_8000_teu_ammonia") *    Variable("container_8000_teu_international_share")>,
		<Forecast("orderbook_container_8000_teu_methane") * Variable("container_8000_teu_international_share")>,
		<Forecast("orderbook_container_8000_teu_methanol") *   Variable("container_8000_teu_international_share")>,
	    <Forecast("orderbook_container_8000_teu_oil") *        Variable("container_8000_teu_international_share")>
	]
}

# -------------------------------- container_15000_teu -------------------------------- #

Copy Vessel "container_15000_teu_ice_ammonia" 	    "container_15000_teu_ice_ammonia_international"
Copy Vessel "container_15000_teu_ice_methane" 	"container_15000_teu_ice_methane_international"
Copy Vessel "container_15000_teu_ice_methanol" 	    "container_15000_teu_ice_methanol_international"
Copy Vessel "container_15000_teu_ice_oil" 		    "container_15000_teu_ice_oil_international"

Copy Route "operational_profile_container_15000_teu"   "operational_profile_container_15000_teu_international"

Vessel "container_15000_teu_*_international" {
	Route = Route("operational_profile_container_15000_teu_international")
}

Fleet "container_15000_teu_international" {

	Vessels = [
		Vessel("container_15000_teu_ice_ammonia_international"),
		Vessel("container_15000_teu_ice_methane_international"),
		Vessel("container_15000_teu_ice_methanol_international"),
	    Vessel("container_15000_teu_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_container_15000_teu") * Variable("container_15000_teu_international_share")>

	Orderbooks = [
		<Forecast("orderbook_container_15000_teu_ammonia") *    Variable("container_15000_teu_international_share")>,
		<Forecast("orderbook_container_15000_teu_methane") * Variable("container_15000_teu_international_share")>,
		<Forecast("orderbook_container_15000_teu_methanol") *   Variable("container_15000_teu_international_share")>,
	    <Forecast("orderbook_container_15000_teu_oil") *        Variable("container_15000_teu_international_share")>
	]
}

# -------------------------------- cruise_25k_gt -------------------------------- #

Copy Vessel "cruise_25k_gt_ice_methane" 	   "cruise_25k_gt_ice_methane_international"
Copy Vessel "cruise_25k_gt_ice_methanol" 	   "cruise_25k_gt_ice_methanol_international"
Copy Vessel "cruise_25k_gt_ice_oil" 		   "cruise_25k_gt_ice_oil_international"

Copy Route "operational_profile_cruise_25k_gt"   "operational_profile_cruise_25k_gt_international"

Vessel "cruise_25k_gt_*_international" {
	Route = Route("operational_profile_cruise_25k_gt_international")
}

Fleet "cruise_25k_gt_international" {

	Vessels = [
		Vessel("cruise_25k_gt_ice_methane_international"),
		Vessel("cruise_25k_gt_ice_methanol_international"),
	    Vessel("cruise_25k_gt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_cruise_25k_gt") * Variable("cruise_25k_gt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_cruise_25k_gt_methane") * Variable("cruise_25k_gt_international_share")>,
		<Forecast("orderbook_cruise_25k_gt_methanol") *   Variable("cruise_25k_gt_international_share")>,
	    <Forecast("orderbook_cruise_25k_gt_oil") *        Variable("cruise_25k_gt_international_share")>
	]
}

# -------------------------------- cruise_100k_gt -------------------------------- #

Copy Vessel "cruise_100k_gt_ice_methane" 	  "cruise_100k_gt_ice_methane_international"
Copy Vessel "cruise_100k_gt_ice_methanol" 	  "cruise_100k_gt_ice_methanol_international"
Copy Vessel "cruise_100k_gt_ice_oil" 		  "cruise_100k_gt_ice_oil_international"

Copy Route "operational_profile_cruise_100k_gt"   "operational_profile_cruise_100k_gt_international"

Vessel "cruise_100k_gt_*_international" {
	Route = Route("operational_profile_cruise_100k_gt_international")
}

Fleet "cruise_100k_gt_international" {

	Vessels = [
		Vessel("cruise_100k_gt_ice_methane_international"),
		Vessel("cruise_100k_gt_ice_methanol_international"),
	    Vessel("cruise_100k_gt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_cruise_100k_gt") * Variable("cruise_100k_gt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_cruise_100k_gt_methane") * Variable("cruise_100k_gt_international_share")>,
		<Forecast("orderbook_cruise_100k_gt_methanol") *   Variable("cruise_100k_gt_international_share")>,
	    <Forecast("orderbook_cruise_100k_gt_oil") *        Variable("cruise_100k_gt_international_share")>
	]
}

# -------------------------------- cruise_175k_gt -------------------------------- #

Copy Vessel "cruise_175k_gt_ice_methane"   "cruise_175k_gt_ice_methane_international"
Copy Vessel "cruise_175k_gt_ice_methanol" 	  "cruise_175k_gt_ice_methanol_international"
Copy Vessel "cruise_175k_gt_ice_oil" 		  "cruise_175k_gt_ice_oil_international"

Copy Route "operational_profile_cruise_175k_gt"   "operational_profile_cruise_175k_gt_international"

Vessel "cruise_175k_gt_*_international" {
	Route = Route("operational_profile_cruise_175k_gt_international")
}

Fleet "cruise_175k_gt_international" {

	Vessels = [
		Vessel("cruise_175k_gt_ice_methane_international"),
		Vessel("cruise_175k_gt_ice_methanol_international"),
	    Vessel("cruise_175k_gt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_cruise_175k_gt") * Variable("cruise_175k_gt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_cruise_175k_gt_methane") * Variable("cruise_175k_gt_international_share")>,
		<Forecast("orderbook_cruise_175k_gt_methanol") *   Variable("cruise_175k_gt_international_share")>,
	    <Forecast("orderbook_cruise_175k_gt_oil") *        Variable("cruise_175k_gt_international_share")>
	]
}

# -------------------------------- ferry -------------------------------- #

Copy Vessel "ferry_ice_methane" 	      "ferry_ice_methane_international"
Copy Vessel "ferry_ice_methanol" 	      "ferry_ice_methanol_international"
Copy Vessel "ferry_ice_oil" 		      "ferry_ice_oil_international"

Copy Route "operational_profile_ferry"   "operational_profile_ferry_international"

Vessel "ferry_*_international" {
	Route = Route("operational_profile_ferry_international")
}

Fleet "ferry_international" {

	Vessels = [
		Vessel("ferry_ice_methane_international"),
		Vessel("ferry_ice_methanol_international"),
	    Vessel("ferry_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_ferry") * Variable("ferry_international_share")>

	Orderbooks = [
		<Forecast("orderbook_ferry_methane") * Variable("ferry_international_share")>,
		<Forecast("orderbook_ferry_methanol") *   Variable("ferry_international_share")>,
	    <Forecast("orderbook_ferry_oil") *        Variable("ferry_international_share")>
	]
}

# -------------------------------- gas_carrier_100k_cbm -------------------------------- #

Copy Vessel "gas_carrier_100k_cbm_ice_ammonia" 	  "gas_carrier_100k_cbm_ice_ammonia_international"
Copy Vessel "gas_carrier_100k_cbm_ice_methane" "gas_carrier_100k_cbm_ice_methane_international"
Copy Vessel "gas_carrier_100k_cbm_ice_methanol"   "gas_carrier_100k_cbm_ice_methanol_international"
Copy Vessel "gas_carrier_100k_cbm_ice_oil" 		  "gas_carrier_100k_cbm_ice_oil_international"

Copy Route "operational_profile_gas_carrier_100k_cbm"   "operational_profile_gas_carrier_100k_cbm_international"

Vessel "gas_carrier_100k_cbm_*_international" {
	Route = Route("operational_profile_gas_carrier_100k_cbm_international")
}

Fleet "gas_carrier_100k_cbm_international" {

	Vessels = [
		Vessel("gas_carrier_100k_cbm_ice_ammonia_international"),
		Vessel("gas_carrier_100k_cbm_ice_methane_international"),
		Vessel("gas_carrier_100k_cbm_ice_methanol_international"),
	    Vessel("gas_carrier_100k_cbm_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_gas_carrier_100k_cbm") * Variable("gas_carrier_100k_cbm_international_share")>

	Orderbooks = [
		<Forecast("orderbook_gas_carrier_100k_cbm_ammonia") *    Variable("gas_carrier_100k_cbm_international_share")>,
		<Forecast("orderbook_gas_carrier_100k_cbm_methane") * Variable("gas_carrier_100k_cbm_international_share")>,
		<Forecast("orderbook_gas_carrier_100k_cbm_methanol") *   Variable("gas_carrier_100k_cbm_international_share")>,
	    <Forecast("orderbook_gas_carrier_100k_cbm_oil") *        Variable("gas_carrier_100k_cbm_international_share")>
	]
}

# -------------------------------- general_cargo -------------------------------- #

Copy Vessel "general_cargo_ice_ammonia"     "general_cargo_ice_ammonia_international"
Copy Vessel "general_cargo_ice_methane" 	"general_cargo_ice_methane_international"
Copy Vessel "general_cargo_ice_methanol"    "general_cargo_ice_methanol_international"
Copy Vessel "general_cargo_ice_oil" 	    "general_cargo_ice_oil_international"

Copy Route "operational_profile_general_cargo"   "operational_profile_general_cargo_international"

Vessel "general_cargo_*_international" {
	Route = Route("operational_profile_general_cargo_international")
}

Fleet "general_cargo_international" {

	Vessels = [
		Vessel("general_cargo_ice_ammonia_international"),
		Vessel("general_cargo_ice_methane_international"),
		Vessel("general_cargo_ice_methanol_international"),
	    Vessel("general_cargo_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_general_cargo") * Variable("general_cargo_international_share")>

	Orderbooks = [
		<Forecast("orderbook_general_cargo_ammonia") *    Variable("general_cargo_international_share")>,
		<Forecast("orderbook_general_cargo_methane") * Variable("general_cargo_international_share")>,
		<Forecast("orderbook_general_cargo_methanol") *   Variable("general_cargo_international_share")>,
	    <Forecast("orderbook_general_cargo_oil") *        Variable("general_cargo_international_share")>
	]
}

# -------------------------------- offshore -------------------------------- #

Copy Vessel "offshore_ice_ammonia" 	    "offshore_ice_ammonia_international"
Copy Vessel "offshore_ice_methane"   "offshore_ice_methane_international"
Copy Vessel "offshore_ice_methanol" 	"offshore_ice_methanol_international"
Copy Vessel "offshore_ice_oil" 		    "offshore_ice_oil_international"

Copy Route "operational_profile_offshore"   "operational_profile_offshore_international"

Vessel "offshore_*_international" {
	Route = Route("operational_profile_offshore_international")
}

Fleet "offshore_international" {

	Vessels = [
		Vessel("offshore_ice_ammonia_international"),
		Vessel("offshore_ice_methane_international"),
		Vessel("offshore_ice_methanol_international"),
	    Vessel("offshore_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_offshore") * Variable("offshore_international_share")>

	Orderbooks = [
		<Forecast("orderbook_offshore_ammonia") *    Variable("offshore_international_share")>,
		<Forecast("orderbook_offshore_methane") * Variable("offshore_international_share")>,
		<Forecast("orderbook_offshore_methanol") *   Variable("offshore_international_share")>,
	    <Forecast("orderbook_offshore_oil") *        Variable("offshore_international_share")>
	]
}

# -------------------------------- other -------------------------------- #

Copy Vessel "other_ice_ammonia" 	"other_ice_ammonia_international"
Copy Vessel "other_ice_methane"  "other_ice_methane_international"
Copy Vessel "other_ice_methanol" 	"other_ice_methanol_international"
Copy Vessel "other_ice_oil" 		"other_ice_oil_international"

Copy Route "operational_profile_other"   "operational_profile_other_international"

Vessel "other_*_international" {
	Route = Route("operational_profile_other_international")
}

Fleet "other_international" {

	Vessels = [
		Vessel("other_ice_ammonia_international"),
		Vessel("other_ice_methane_international"),
		Vessel("other_ice_methanol_international"),
	    Vessel("other_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_other") * Variable("other_international_share")>

	Orderbooks = [
		<Forecast("orderbook_other_ammonia") *    Variable("other_international_share")>,
		<Forecast("orderbook_other_methane") * Variable("other_international_share")>,
		<Forecast("orderbook_other_methanol") *   Variable("other_international_share")>,
	    <Forecast("orderbook_other_oil") *        Variable("other_international_share")>
	]
}

# -------------------------------- roro_4000_ceu -------------------------------- #

Copy Vessel "roro_4000_ceu_ice_ammonia"     "roro_4000_ceu_ice_ammonia_international"
Copy Vessel "roro_4000_ceu_ice_methane" 	"roro_4000_ceu_ice_methane_international"
Copy Vessel "roro_4000_ceu_ice_methanol"    "roro_4000_ceu_ice_methanol_international"
Copy Vessel "roro_4000_ceu_ice_oil" 	    "roro_4000_ceu_ice_oil_international"

Copy Route "operational_profile_roro_4000_ceu"   "operational_profile_roro_4000_ceu_international"

Vessel "roro_4000_ceu_*_international" {
	Route = Route("operational_profile_roro_4000_ceu_international")
}

Fleet "roro_4000_ceu_international" {

	Vessels = [
		Vessel("roro_4000_ceu_ice_ammonia_international"),
		Vessel("roro_4000_ceu_ice_methane_international"),
		Vessel("roro_4000_ceu_ice_methanol_international"),
	    Vessel("roro_4000_ceu_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_roro_4000_ceu") * Variable("roro_4000_ceu_international_share")>

	Orderbooks = [
		<Forecast("orderbook_roro_4000_ceu_ammonia") *    Variable("roro_4000_ceu_international_share")>,
		<Forecast("orderbook_roro_4000_ceu_methane") * Variable("roro_4000_ceu_international_share")>,
		<Forecast("orderbook_roro_4000_ceu_methanol") *   Variable("roro_4000_ceu_international_share")>,
	    <Forecast("orderbook_roro_4000_ceu_oil") *        Variable("roro_4000_ceu_international_share")>
	]
}

# -------------------------------- roro_7000_ceu -------------------------------- #

Copy Vessel "roro_7000_ceu_ice_ammonia" 	"roro_7000_ceu_ice_ammonia_international"
Copy Vessel "roro_7000_ceu_ice_methane"  "roro_7000_ceu_ice_methane_international"
Copy Vessel "roro_7000_ceu_ice_methanol" 	"roro_7000_ceu_ice_methanol_international"
Copy Vessel "roro_7000_ceu_ice_oil" 		"roro_7000_ceu_ice_oil_international"

Copy Route "operational_profile_roro_7000_ceu"   "operational_profile_roro_7000_ceu_international"

Vessel "roro_7000_ceu_*_international" {
	Route = Route("operational_profile_roro_7000_ceu_international")
}

Fleet "roro_7000_ceu_international" {

	Vessels = [
		Vessel("roro_7000_ceu_ice_ammonia_international"),
		Vessel("roro_7000_ceu_ice_methane_international"),
		Vessel("roro_7000_ceu_ice_methanol_international"),
	    Vessel("roro_7000_ceu_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_roro_7000_ceu") * Variable("roro_7000_ceu_international_share")>

	Orderbooks = [
		<Forecast("orderbook_roro_7000_ceu_ammonia") *    Variable("roro_7000_ceu_international_share")>,
		<Forecast("orderbook_roro_7000_ceu_methane") * Variable("roro_7000_ceu_international_share")>,
		<Forecast("orderbook_roro_7000_ceu_methanol") *   Variable("roro_7000_ceu_international_share")>,
	    <Forecast("orderbook_roro_7000_ceu_oil") *        Variable("roro_7000_ceu_international_share")>
	]
}

# -------------------------------- tanker_7500_dwt -------------------------------- #

Copy Vessel "tanker_7500_dwt_ice_ammonia" 	 "tanker_7500_dwt_ice_ammonia_international"
Copy Vessel "tanker_7500_dwt_ice_methane" "tanker_7500_dwt_ice_methane_international"
Copy Vessel "tanker_7500_dwt_ice_methanol"   "tanker_7500_dwt_ice_methanol_international"
Copy Vessel "tanker_7500_dwt_ice_oil" 		 "tanker_7500_dwt_ice_oil_international"

Copy Route "operational_profile_tanker_7500_dwt"   "operational_profile_tanker_7500_dwt_international"

Vessel "tanker_7500_dwt_*_international" {
	Route = Route("operational_profile_tanker_7500_dwt_international")
}

Fleet "tanker_7500_dwt_international" {

	Vessels = [
		Vessel("tanker_7500_dwt_ice_ammonia_international"),
		Vessel("tanker_7500_dwt_ice_methane_international"),
		Vessel("tanker_7500_dwt_ice_methanol_international"),
	    Vessel("tanker_7500_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_tanker_7500_dwt") * Variable("tanker_7500_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_tanker_7500_dwt_ammonia") *    Variable("tanker_7500_dwt_international_share")>,
		<Forecast("orderbook_tanker_7500_dwt_methane") * Variable("tanker_7500_dwt_international_share")>,
		<Forecast("orderbook_tanker_7500_dwt_methanol") *   Variable("tanker_7500_dwt_international_share")>,
	    <Forecast("orderbook_tanker_7500_dwt_oil") *        Variable("tanker_7500_dwt_international_share")>
	]
}

# -------------------------------- tanker_47k_dwt -------------------------------- #

Copy Vessel "tanker_47k_dwt_ice_ammonia" 	"tanker_47k_dwt_ice_ammonia_international"
Copy Vessel "tanker_47k_dwt_ice_methane" "tanker_47k_dwt_ice_methane_international"
Copy Vessel "tanker_47k_dwt_ice_methanol" 	"tanker_47k_dwt_ice_methanol_international"
Copy Vessel "tanker_47k_dwt_ice_oil" 		"tanker_47k_dwt_ice_oil_international"

Copy Route "operational_profile_tanker_47k_dwt"   "operational_profile_tanker_47k_dwt_international"

Vessel "tanker_47k_dwt_*_international" {
	Route = Route("operational_profile_tanker_47k_dwt_international")
}

Fleet "tanker_47k_dwt_international" {

	Vessels = [
		Vessel("tanker_47k_dwt_ice_ammonia_international"),
		Vessel("tanker_47k_dwt_ice_methane_international"),
		Vessel("tanker_47k_dwt_ice_methanol_international"),
	    Vessel("tanker_47k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_tanker_47k_dwt") * Variable("tanker_47k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_tanker_47k_dwt_ammonia") *    Variable("tanker_47k_dwt_international_share")>,
		<Forecast("orderbook_tanker_47k_dwt_methane") * Variable("tanker_47k_dwt_international_share")>,
		<Forecast("orderbook_tanker_47k_dwt_methanol") *   Variable("tanker_47k_dwt_international_share")>,
	    <Forecast("orderbook_tanker_47k_dwt_oil") *        Variable("tanker_47k_dwt_international_share")>
	]
}

# -------------------------------- tanker_127k_dwt -------------------------------- #

Copy Vessel "tanker_127k_dwt_ice_ammonia" 	 "tanker_127k_dwt_ice_ammonia_international"
Copy Vessel "tanker_127k_dwt_ice_methane" "tanker_127k_dwt_ice_methane_international"
Copy Vessel "tanker_127k_dwt_ice_methanol" 	 "tanker_127k_dwt_ice_methanol_international"
Copy Vessel "tanker_127k_dwt_ice_oil" 		 "tanker_127k_dwt_ice_oil_international"

Copy Route "operational_profile_tanker_127k_dwt"   "operational_profile_tanker_127k_dwt_international"

Vessel "tanker_127k_dwt_*_international" {
	Route = Route("operational_profile_tanker_127k_dwt_international")
}

Fleet "tanker_127k_dwt_international" {

	Vessels = [
		Vessel("tanker_127k_dwt_ice_ammonia_international"),
		Vessel("tanker_127k_dwt_ice_methane_international"),
		Vessel("tanker_127k_dwt_ice_methanol_international"),
	    Vessel("tanker_127k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_tanker_127k_dwt") * Variable("tanker_127k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_tanker_127k_dwt_ammonia") *    Variable("tanker_127k_dwt_international_share")>,
		<Forecast("orderbook_tanker_127k_dwt_methane") * Variable("tanker_127k_dwt_international_share")>,
		<Forecast("orderbook_tanker_127k_dwt_methanol") *   Variable("tanker_127k_dwt_international_share")>,
	    <Forecast("orderbook_tanker_127k_dwt_oil") *        Variable("tanker_127k_dwt_international_share")>
	]
}


# -------------------------------- tanker_300k_dwt -------------------------------- #

Copy Vessel "tanker_300k_dwt_ice_ammonia" 	 "tanker_300k_dwt_ice_ammonia_international"
Copy Vessel "tanker_300k_dwt_ice_methane" "tanker_300k_dwt_ice_methane_international"
Copy Vessel "tanker_300k_dwt_ice_methanol" 	 "tanker_300k_dwt_ice_methanol_international"
Copy Vessel "tanker_300k_dwt_ice_oil" 		 "tanker_300k_dwt_ice_oil_international"

Copy Route "operational_profile_tanker_300k_dwt"   "operational_profile_tanker_300k_dwt_international"

Vessel "tanker_300k_dwt_*_international" {
	Route = Route("operational_profile_tanker_300k_dwt_international")
}

Fleet "tanker_300k_dwt_international" {

	Vessels = [
		Vessel("tanker_300k_dwt_ice_ammonia_international"),
		Vessel("tanker_300k_dwt_ice_methane_international"),
		Vessel("tanker_300k_dwt_ice_methanol_international"),
	    Vessel("tanker_300k_dwt_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_tanker_300k_dwt") * Variable("tanker_300k_dwt_international_share")>

	Orderbooks = [
		<Forecast("orderbook_tanker_300k_dwt_ammonia") *    Variable("tanker_300k_dwt_international_share")>,
		<Forecast("orderbook_tanker_300k_dwt_methane") * Variable("tanker_300k_dwt_international_share")>,
		<Forecast("orderbook_tanker_300k_dwt_methanol") *   Variable("tanker_300k_dwt_international_share")>,
	    <Forecast("orderbook_tanker_300k_dwt_oil") *        Variable("tanker_300k_dwt_international_share")>
	]
}

# -------------------------------- tug -------------------------------- #

Copy Vessel "tug_ice_ammonia" 	    "tug_ice_ammonia_international"
Copy Vessel "tug_ice_methane" 	"tug_ice_methane_international"
Copy Vessel "tug_ice_methanol" 	    "tug_ice_methanol_international"
Copy Vessel "tug_ice_oil" 		    "tug_ice_oil_international"

Copy Route "operational_profile_tug"   "operational_profile_tug_international"

Vessel "tug_*_international" {
	Route = Route("operational_profile_tug_international")
}

Fleet "tug_international" {

	Vessels = [
		Vessel("tug_ice_ammonia_international"),
		Vessel("tug_ice_methane_international"),
		Vessel("tug_ice_methanol_international"),
	    Vessel("tug_ice_oil_international")
	]

	InitialVessels = <Variable("initial_vessels_tug") * Variable("tug_international_share")>

	Orderbooks = [
		<Forecast("orderbook_tug_ammonia") *    Variable("tug_international_share")>,
		<Forecast("orderbook_tug_methane") * Variable("tug_international_share")>,
		<Forecast("orderbook_tug_methanol") *   Variable("tug_international_share")>,
	    <Forecast("orderbook_tug_oil") *        Variable("tug_international_share")>
	]
}
