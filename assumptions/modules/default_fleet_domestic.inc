# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Copy Fleet "bulk_carrier_26k_dwt" 	"bulk_carrier_26k_dwt_domestic"
Copy Fleet "bulk_carrier_52k_dwt" 	"bulk_carrier_52k_dwt_domestic"
Copy Fleet "bulk_carrier_80k_dwt" 	"bulk_carrier_80k_dwt_domestic"
Copy Fleet "bulk_carrier_200k_dwt" 	"bulk_carrier_200k_dwt_domestic"

Copy Fleet "container_1500_teu" 	"container_1500_teu_domestic"
Copy Fleet "container_4500_teu" 	"container_4500_teu_domestic"
Copy Fleet "container_8000_teu" 	"container_8000_teu_domestic"
Copy Fleet "container_15000_teu" 	"container_15000_teu_domestic"

Copy Fleet "cruise_25k_gt" 			"cruise_25k_gt_domestic"
Copy Fleet "cruise_100k_gt" 		"cruise_100k_gt_domestic"
Copy Fleet "cruise_175k_gt" 		"cruise_175k_gt_domestic"

Copy Fleet "ferry" 					"ferry_domestic"

Copy Fleet "gas_carrier_100k_cbm" 	"gas_carrier_100k_cbm_domestic"

Copy Fleet "general_cargo" 			"general_cargo_domestic"

Copy Fleet "offshore" 				"offshore_domestic"

Copy Fleet "other" 					"other_domestic"

Copy Fleet "roro_4000_ceu" 			"roro_4000_ceu_domestic"
Copy Fleet "roro_7000_ceu" 			"roro_7000_ceu_domestic"

Copy Fleet "tanker_7500_dwt" 		"tanker_7500_dwt_domestic"
Copy Fleet "tanker_47k_dwt" 		"tanker_47k_dwt_domestic"
Copy Fleet "tanker_127k_dwt" 		"tanker_127k_dwt_domestic"
Copy Fleet "tanker_300k_dwt" 		"tanker_300k_dwt_domestic"

Copy Fleet "tug" 					"tug_domestic"

# -------------------------------- bulk_carrier_26k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_26k_dwt_ice_ammonia" 	    "bulk_carrier_26k_dwt_ice_ammonia_domestic"
Copy Vessel "bulk_carrier_26k_dwt_ice_methane" 	"bulk_carrier_26k_dwt_ice_methane_domestic"
Copy Vessel "bulk_carrier_26k_dwt_ice_methanol" 	"bulk_carrier_26k_dwt_ice_methanol_domestic"
Copy Vessel "bulk_carrier_26k_dwt_ice_oil" 		    "bulk_carrier_26k_dwt_ice_oil_domestic"

Copy Route "operational_profile_bulk_carrier_26k_dwt"   "operational_profile_bulk_carrier_26k_dwt_domestic"

Vessel "bulk_carrier_26k_dwt_*_domestic" {
	Route = Route("operational_profile_bulk_carrier_26k_dwt_domestic")
}

Fleet "bulk_carrier_26k_dwt_domestic" {

	Vessels = [
		Vessel("bulk_carrier_26k_dwt_ice_ammonia_domestic"),
		Vessel("bulk_carrier_26k_dwt_ice_methane_domestic"),
		Vessel("bulk_carrier_26k_dwt_ice_methanol_domestic"),
	    Vessel("bulk_carrier_26k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_26k_dwt") * (1 - Variable("bulk_carrier_26k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_26k_dwt_ammonia") *    (1 - Variable("bulk_carrier_26k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_26k_dwt_methane") * (1 - Variable("bulk_carrier_26k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_26k_dwt_methanol") *   (1 - Variable("bulk_carrier_26k_dwt_international_share"))>,
	    <Forecast("orderbook_bulk_carrier_26k_dwt_oil") *        (1 - Variable("bulk_carrier_26k_dwt_international_share"))>
	]
}

# -------------------------------- bulk_carrier_52k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_52k_dwt_ice_ammonia" 	    "bulk_carrier_52k_dwt_ice_ammonia_domestic"
Copy Vessel "bulk_carrier_52k_dwt_ice_methane" 	"bulk_carrier_52k_dwt_ice_methane_domestic"
Copy Vessel "bulk_carrier_52k_dwt_ice_methanol" 	"bulk_carrier_52k_dwt_ice_methanol_domestic"
Copy Vessel "bulk_carrier_52k_dwt_ice_oil" 		    "bulk_carrier_52k_dwt_ice_oil_domestic"

Copy Route "operational_profile_bulk_carrier_52k_dwt"   "operational_profile_bulk_carrier_52k_dwt_domestic"

Vessel "bulk_carrier_52k_dwt_*_domestic" {
	Route = Route("operational_profile_bulk_carrier_52k_dwt_domestic")
}

Fleet "bulk_carrier_52k_dwt_domestic" {

	Vessels = [
		Vessel("bulk_carrier_52k_dwt_ice_ammonia_domestic"),
		Vessel("bulk_carrier_52k_dwt_ice_methane_domestic"),
		Vessel("bulk_carrier_52k_dwt_ice_methanol_domestic"),
	    Vessel("bulk_carrier_52k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_52k_dwt") * (1 - Variable("bulk_carrier_52k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_52k_dwt_ammonia") *    (1 - Variable("bulk_carrier_52k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_52k_dwt_methane") * (1 - Variable("bulk_carrier_52k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_52k_dwt_methanol") *   (1 - Variable("bulk_carrier_52k_dwt_international_share"))>,
	    <Forecast("orderbook_bulk_carrier_52k_dwt_oil") *        (1 - Variable("bulk_carrier_52k_dwt_international_share"))>
	]
}


# -------------------------------- bulk_carrier_80k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_80k_dwt_ice_ammonia" 	    "bulk_carrier_80k_dwt_ice_ammonia_domestic"
Copy Vessel "bulk_carrier_80k_dwt_ice_methane" 	"bulk_carrier_80k_dwt_ice_methane_domestic"
Copy Vessel "bulk_carrier_80k_dwt_ice_methanol" 	"bulk_carrier_80k_dwt_ice_methanol_domestic"
Copy Vessel "bulk_carrier_80k_dwt_ice_oil" 		    "bulk_carrier_80k_dwt_ice_oil_domestic"

Copy Route "operational_profile_bulk_carrier_80k_dwt"   "operational_profile_bulk_carrier_80k_dwt_domestic"

Vessel "bulk_carrier_80k_dwt_*_domestic" {
	Route = Route("operational_profile_bulk_carrier_80k_dwt_domestic")
}

Fleet "bulk_carrier_80k_dwt_domestic" {

	Vessels = [
		Vessel("bulk_carrier_80k_dwt_ice_ammonia_domestic"),
		Vessel("bulk_carrier_80k_dwt_ice_methane_domestic"),
		Vessel("bulk_carrier_80k_dwt_ice_methanol_domestic"),
	    Vessel("bulk_carrier_80k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_80k_dwt") * (1 - Variable("bulk_carrier_80k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_80k_dwt_ammonia") *    (1 - Variable("bulk_carrier_80k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_80k_dwt_methane") * (1 - Variable("bulk_carrier_80k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_80k_dwt_methanol") *   (1 - Variable("bulk_carrier_80k_dwt_international_share"))>,
	    <Forecast("orderbook_bulk_carrier_80k_dwt_oil") *        (1 - Variable("bulk_carrier_80k_dwt_international_share"))>
	]
}

# -------------------------------- bulk_carrier_200k_dwt -------------------------------- #

Copy Vessel "bulk_carrier_200k_dwt_ice_ammonia" 	  "bulk_carrier_200k_dwt_ice_ammonia_domestic"
Copy Vessel "bulk_carrier_200k_dwt_ice_methane"   "bulk_carrier_200k_dwt_ice_methane_domestic"
Copy Vessel "bulk_carrier_200k_dwt_ice_methanol" 	  "bulk_carrier_200k_dwt_ice_methanol_domestic"
Copy Vessel "bulk_carrier_200k_dwt_ice_oil" 		  "bulk_carrier_200k_dwt_ice_oil_domestic"

Copy Route "operational_profile_bulk_carrier_200k_dwt"   "operational_profile_bulk_carrier_200k_dwt_domestic"

Vessel "bulk_carrier_200k_dwt_*_domestic" {
	Route = Route("operational_profile_bulk_carrier_200k_dwt_domestic")
}

Fleet "bulk_carrier_200k_dwt_domestic" {

	Vessels = [
		Vessel("bulk_carrier_200k_dwt_ice_ammonia_domestic"),
		Vessel("bulk_carrier_200k_dwt_ice_methane_domestic"),
		Vessel("bulk_carrier_200k_dwt_ice_methanol_domestic"),
	    Vessel("bulk_carrier_200k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_bulk_carrier_200k_dwt") * (1 - Variable("bulk_carrier_200k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_bulk_carrier_200k_dwt_ammonia") *    (1 - Variable("bulk_carrier_200k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_200k_dwt_methane") * (1 - Variable("bulk_carrier_200k_dwt_international_share"))>,
		<Forecast("orderbook_bulk_carrier_200k_dwt_methanol") *   (1 - Variable("bulk_carrier_200k_dwt_international_share"))>,
	    <Forecast("orderbook_bulk_carrier_200k_dwt_oil") *        (1 - Variable("bulk_carrier_200k_dwt_international_share"))>
	]
}

# -------------------------------- container_1500_teu -------------------------------- #

Copy Vessel "container_1500_teu_ice_ammonia" 	    "container_1500_teu_ice_ammonia_domestic"
Copy Vessel "container_1500_teu_ice_methane" 	"container_1500_teu_ice_methane_domestic"
Copy Vessel "container_1500_teu_ice_methanol" 	    "container_1500_teu_ice_methanol_domestic"
Copy Vessel "container_1500_teu_ice_oil" 		    "container_1500_teu_ice_oil_domestic"

Copy Route "operational_profile_container_1500_teu"   "operational_profile_container_1500_teu_domestic"

Vessel "container_1500_teu_*_domestic" {
	Route = Route("operational_profile_container_1500_teu_domestic")
}

Fleet "container_1500_teu_domestic" {

	Vessels = [
		Vessel("container_1500_teu_ice_ammonia_domestic"),
		Vessel("container_1500_teu_ice_methane_domestic"),
		Vessel("container_1500_teu_ice_methanol_domestic"),
	    Vessel("container_1500_teu_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_container_1500_teu") * (1 - Variable("container_1500_teu_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_container_1500_teu_ammonia") *    (1 - Variable("container_1500_teu_international_share"))>,
		<Forecast("orderbook_container_1500_teu_methane") * (1 - Variable("container_1500_teu_international_share"))>,
		<Forecast("orderbook_container_1500_teu_methanol") *   (1 - Variable("container_1500_teu_international_share"))>,
	    <Forecast("orderbook_container_1500_teu_oil") *        (1 - Variable("container_1500_teu_international_share"))>
	]
}

# -------------------------------- container_4500_teu -------------------------------- #

Copy Vessel "container_4500_teu_ice_ammonia" 	    "container_4500_teu_ice_ammonia_domestic"
Copy Vessel "container_4500_teu_ice_methane" 	"container_4500_teu_ice_methane_domestic"
Copy Vessel "container_4500_teu_ice_methanol" 	    "container_4500_teu_ice_methanol_domestic"
Copy Vessel "container_4500_teu_ice_oil" 		    "container_4500_teu_ice_oil_domestic"

Copy Route "operational_profile_container_4500_teu"   "operational_profile_container_4500_teu_domestic"

Vessel "container_4500_teu_*_domestic" {
	Route = Route("operational_profile_container_4500_teu_domestic")
}

Fleet "container_4500_teu_domestic" {

	Vessels = [
		Vessel("container_4500_teu_ice_ammonia_domestic"),
		Vessel("container_4500_teu_ice_methane_domestic"),
		Vessel("container_4500_teu_ice_methanol_domestic"),
	    Vessel("container_4500_teu_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_container_4500_teu") * (1 - Variable("container_4500_teu_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_container_4500_teu_ammonia") *    (1 - Variable("container_4500_teu_international_share"))>,
		<Forecast("orderbook_container_4500_teu_methane") * (1 - Variable("container_4500_teu_international_share"))>,
		<Forecast("orderbook_container_4500_teu_methanol") *   (1 - Variable("container_4500_teu_international_share"))>,
	    <Forecast("orderbook_container_4500_teu_oil") *        (1 - Variable("container_4500_teu_international_share"))>
	]
}

# -------------------------------- container_8000_teu -------------------------------- #

Copy Vessel "container_8000_teu_ice_ammonia" 	    "container_8000_teu_ice_ammonia_domestic"
Copy Vessel "container_8000_teu_ice_methane" 	"container_8000_teu_ice_methane_domestic"
Copy Vessel "container_8000_teu_ice_methanol" 	    "container_8000_teu_ice_methanol_domestic"
Copy Vessel "container_8000_teu_ice_oil" 		    "container_8000_teu_ice_oil_domestic"

Copy Route "operational_profile_container_8000_teu"   "operational_profile_container_8000_teu_domestic"

Vessel "container_8000_teu_*_domestic" {
	Route = Route("operational_profile_container_8000_teu_domestic")
}

Fleet "container_8000_teu_domestic" {

	Vessels = [
		Vessel("container_8000_teu_ice_ammonia_domestic"),
		Vessel("container_8000_teu_ice_methane_domestic"),
		Vessel("container_8000_teu_ice_methanol_domestic"),
	    Vessel("container_8000_teu_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_container_8000_teu") * (1 - Variable("container_8000_teu_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_container_8000_teu_ammonia") *    (1 - Variable("container_8000_teu_international_share"))>,
		<Forecast("orderbook_container_8000_teu_methane") * (1 - Variable("container_8000_teu_international_share"))>,
		<Forecast("orderbook_container_8000_teu_methanol") *   (1 - Variable("container_8000_teu_international_share"))>,
	    <Forecast("orderbook_container_8000_teu_oil") *        (1 - Variable("container_8000_teu_international_share"))>
	]
}

# -------------------------------- container_15000_teu -------------------------------- #

Copy Vessel "container_15000_teu_ice_ammonia" 	    "container_15000_teu_ice_ammonia_domestic"
Copy Vessel "container_15000_teu_ice_methane" 	"container_15000_teu_ice_methane_domestic"
Copy Vessel "container_15000_teu_ice_methanol" 	    "container_15000_teu_ice_methanol_domestic"
Copy Vessel "container_15000_teu_ice_oil" 		    "container_15000_teu_ice_oil_domestic"

Copy Route "operational_profile_container_15000_teu"   "operational_profile_container_15000_teu_domestic"

Vessel "container_15000_teu_*_domestic" {
	Route = Route("operational_profile_container_15000_teu_domestic")
}

Fleet "container_15000_teu_domestic" {

	Vessels = [
		Vessel("container_15000_teu_ice_ammonia_domestic"),
		Vessel("container_15000_teu_ice_methane_domestic"),
		Vessel("container_15000_teu_ice_methanol_domestic"),
	    Vessel("container_15000_teu_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_container_15000_teu") * (1 - Variable("container_15000_teu_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_container_15000_teu_ammonia") *    (1 - Variable("container_15000_teu_international_share"))>,
		<Forecast("orderbook_container_15000_teu_methane") * (1 - Variable("container_15000_teu_international_share"))>,
		<Forecast("orderbook_container_15000_teu_methanol") *   (1 - Variable("container_15000_teu_international_share"))>,
	    <Forecast("orderbook_container_15000_teu_oil") *        (1 - Variable("container_15000_teu_international_share"))>
	]
}

# -------------------------------- cruise_25k_gt -------------------------------- #

Copy Vessel "cruise_25k_gt_ice_methane" 	   "cruise_25k_gt_ice_methane_domestic"
Copy Vessel "cruise_25k_gt_ice_methanol" 	   "cruise_25k_gt_ice_methanol_domestic"
Copy Vessel "cruise_25k_gt_ice_oil" 		   "cruise_25k_gt_ice_oil_domestic"

Copy Route "operational_profile_cruise_25k_gt"   "operational_profile_cruise_25k_gt_domestic"

Vessel "cruise_25k_gt_*_domestic" {
	Route = Route("operational_profile_cruise_25k_gt_domestic")
}

Fleet "cruise_25k_gt_domestic" {

	Vessels = [
		Vessel("cruise_25k_gt_ice_methane_domestic"),
		Vessel("cruise_25k_gt_ice_methanol_domestic"),
	    Vessel("cruise_25k_gt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_cruise_25k_gt") * (1 - Variable("cruise_25k_gt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_cruise_25k_gt_methane") * (1 - Variable("cruise_25k_gt_international_share"))>,
		<Forecast("orderbook_cruise_25k_gt_methanol") *   (1 - Variable("cruise_25k_gt_international_share"))>,
	    <Forecast("orderbook_cruise_25k_gt_oil") *        (1 - Variable("cruise_25k_gt_international_share"))>
	]
}

# -------------------------------- cruise_100k_gt -------------------------------- #

Copy Vessel "cruise_100k_gt_ice_methane" 	  "cruise_100k_gt_ice_methane_domestic"
Copy Vessel "cruise_100k_gt_ice_methanol" 	  "cruise_100k_gt_ice_methanol_domestic"
Copy Vessel "cruise_100k_gt_ice_oil" 		  "cruise_100k_gt_ice_oil_domestic"

Copy Route "operational_profile_cruise_100k_gt"   "operational_profile_cruise_100k_gt_domestic"

Vessel "cruise_100k_gt_*_domestic" {
	Route = Route("operational_profile_cruise_100k_gt_domestic")
}

Fleet "cruise_100k_gt_domestic" {

	Vessels = [
		Vessel("cruise_100k_gt_ice_methane_domestic"),
		Vessel("cruise_100k_gt_ice_methanol_domestic"),
	    Vessel("cruise_100k_gt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_cruise_100k_gt") * (1 - Variable("cruise_100k_gt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_cruise_100k_gt_methane") * (1 - Variable("cruise_100k_gt_international_share"))>,
		<Forecast("orderbook_cruise_100k_gt_methanol") *   (1 - Variable("cruise_100k_gt_international_share"))>,
	    <Forecast("orderbook_cruise_100k_gt_oil") *        (1 - Variable("cruise_100k_gt_international_share"))>
	]
}

# -------------------------------- cruise_175k_gt -------------------------------- #

Copy Vessel "cruise_175k_gt_ice_methane"   "cruise_175k_gt_ice_methane_domestic"
Copy Vessel "cruise_175k_gt_ice_methanol" 	  "cruise_175k_gt_ice_methanol_domestic"
Copy Vessel "cruise_175k_gt_ice_oil" 		  "cruise_175k_gt_ice_oil_domestic"

Copy Route "operational_profile_cruise_175k_gt"   "operational_profile_cruise_175k_gt_domestic"

Vessel "cruise_175k_gt_*_domestic" {
	Route = Route("operational_profile_cruise_175k_gt_domestic")
}

Fleet "cruise_175k_gt_domestic" {

	Vessels = [
		Vessel("cruise_175k_gt_ice_methane_domestic"),
		Vessel("cruise_175k_gt_ice_methanol_domestic"),
	    Vessel("cruise_175k_gt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_cruise_175k_gt") * (1 - Variable("cruise_175k_gt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_cruise_175k_gt_methane") * (1 - Variable("cruise_175k_gt_international_share"))>,
		<Forecast("orderbook_cruise_175k_gt_methanol") *   (1 - Variable("cruise_175k_gt_international_share"))>,
	    <Forecast("orderbook_cruise_175k_gt_oil") *        (1 - Variable("cruise_175k_gt_international_share"))>
	]
}

# -------------------------------- ferry -------------------------------- #

Copy Vessel "ferry_ice_methane" 	      "ferry_ice_methane_domestic"
Copy Vessel "ferry_ice_methanol" 	      "ferry_ice_methanol_domestic"
Copy Vessel "ferry_ice_oil" 		      "ferry_ice_oil_domestic"

Copy Route "operational_profile_ferry"   "operational_profile_ferry_domestic"

Vessel "ferry_*_domestic" {
	Route = Route("operational_profile_ferry_domestic")
}

Fleet "ferry_domestic" {

	Vessels = [
		Vessel("ferry_ice_methane_domestic"),
		Vessel("ferry_ice_methanol_domestic"),
	    Vessel("ferry_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_ferry") * (1 - Variable("ferry_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_ferry_methane") * (1 - Variable("ferry_international_share"))>,
		<Forecast("orderbook_ferry_methanol") *   (1 - Variable("ferry_international_share"))>,
	    <Forecast("orderbook_ferry_oil") *        (1 - Variable("ferry_international_share"))>
	]
}

# -------------------------------- gas_carrier_100k_cbm -------------------------------- #

Copy Vessel "gas_carrier_100k_cbm_ice_ammonia" 	  "gas_carrier_100k_cbm_ice_ammonia_domestic"
Copy Vessel "gas_carrier_100k_cbm_ice_methane" "gas_carrier_100k_cbm_ice_methane_domestic"
Copy Vessel "gas_carrier_100k_cbm_ice_methanol"   "gas_carrier_100k_cbm_ice_methanol_domestic"
Copy Vessel "gas_carrier_100k_cbm_ice_oil" 		  "gas_carrier_100k_cbm_ice_oil_domestic"

Copy Route "operational_profile_gas_carrier_100k_cbm"   "operational_profile_gas_carrier_100k_cbm_domestic"

Vessel "gas_carrier_100k_cbm_*_domestic" {
	Route = Route("operational_profile_gas_carrier_100k_cbm_domestic")
}

Fleet "gas_carrier_100k_cbm_domestic" {

	Vessels = [
		Vessel("gas_carrier_100k_cbm_ice_ammonia_domestic"),
		Vessel("gas_carrier_100k_cbm_ice_methane_domestic"),
		Vessel("gas_carrier_100k_cbm_ice_methanol_domestic"),
	    Vessel("gas_carrier_100k_cbm_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_gas_carrier_100k_cbm") * (1 - Variable("gas_carrier_100k_cbm_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_gas_carrier_100k_cbm_ammonia") *    (1 - Variable("gas_carrier_100k_cbm_international_share"))>,
		<Forecast("orderbook_gas_carrier_100k_cbm_methane") * (1 - Variable("gas_carrier_100k_cbm_international_share"))>,
		<Forecast("orderbook_gas_carrier_100k_cbm_methanol") *   (1 - Variable("gas_carrier_100k_cbm_international_share"))>,
	    <Forecast("orderbook_gas_carrier_100k_cbm_oil") *        (1 - Variable("gas_carrier_100k_cbm_international_share"))>
	]
}

# -------------------------------- general_cargo -------------------------------- #

Copy Vessel "general_cargo_ice_ammonia"     "general_cargo_ice_ammonia_domestic"
Copy Vessel "general_cargo_ice_methane" 	"general_cargo_ice_methane_domestic"
Copy Vessel "general_cargo_ice_methanol"    "general_cargo_ice_methanol_domestic"
Copy Vessel "general_cargo_ice_oil" 	    "general_cargo_ice_oil_domestic"

Copy Route "operational_profile_general_cargo"   "operational_profile_general_cargo_domestic"

Vessel "general_cargo_*_domestic" {
	Route = Route("operational_profile_general_cargo_domestic")
}

Fleet "general_cargo_domestic" {

	Vessels = [
		Vessel("general_cargo_ice_ammonia_domestic"),
		Vessel("general_cargo_ice_methane_domestic"),
		Vessel("general_cargo_ice_methanol_domestic"),
	    Vessel("general_cargo_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_general_cargo") * (1 - Variable("general_cargo_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_general_cargo_ammonia") *    (1 - Variable("general_cargo_international_share"))>,
		<Forecast("orderbook_general_cargo_methane") * (1 - Variable("general_cargo_international_share"))>,
		<Forecast("orderbook_general_cargo_methanol") *   (1 - Variable("general_cargo_international_share"))>,
	    <Forecast("orderbook_general_cargo_oil") *        (1 - Variable("general_cargo_international_share"))>
	]
}

# -------------------------------- offshore -------------------------------- #

Copy Vessel "offshore_ice_ammonia" 	    "offshore_ice_ammonia_domestic"
Copy Vessel "offshore_ice_methane"   "offshore_ice_methane_domestic"
Copy Vessel "offshore_ice_methanol" 	"offshore_ice_methanol_domestic"
Copy Vessel "offshore_ice_oil" 		    "offshore_ice_oil_domestic"

Copy Route "operational_profile_offshore"   "operational_profile_offshore_domestic"

Vessel "offshore_*_domestic" {
	Route = Route("operational_profile_offshore_domestic")
}

Fleet "offshore_domestic" {

	Vessels = [
		Vessel("offshore_ice_ammonia_domestic"),
		Vessel("offshore_ice_methane_domestic"),
		Vessel("offshore_ice_methanol_domestic"),
	    Vessel("offshore_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_offshore") * (1 - Variable("offshore_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_offshore_ammonia") *    (1 - Variable("offshore_international_share"))>,
		<Forecast("orderbook_offshore_methane") * (1 - Variable("offshore_international_share"))>,
		<Forecast("orderbook_offshore_methanol") *   (1 - Variable("offshore_international_share"))>,
	    <Forecast("orderbook_offshore_oil") *        (1 - Variable("offshore_international_share"))>
	]
}

# -------------------------------- other -------------------------------- #

Copy Vessel "other_ice_ammonia" 	"other_ice_ammonia_domestic"
Copy Vessel "other_ice_methane"  "other_ice_methane_domestic"
Copy Vessel "other_ice_methanol" 	"other_ice_methanol_domestic"
Copy Vessel "other_ice_oil" 		"other_ice_oil_domestic"

Copy Route "operational_profile_other"   "operational_profile_other_domestic"

Vessel "other_*_domestic" {
	Route = Route("operational_profile_other_domestic")
}

Fleet "other_domestic" {

	Vessels = [
		Vessel("other_ice_ammonia_domestic"),
		Vessel("other_ice_methane_domestic"),
		Vessel("other_ice_methanol_domestic"),
	    Vessel("other_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_other") * (1 - Variable("other_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_other_ammonia") *    (1 - Variable("other_international_share"))>,
		<Forecast("orderbook_other_methane") * (1 - Variable("other_international_share"))>,
		<Forecast("orderbook_other_methanol") *   (1 - Variable("other_international_share"))>,
	    <Forecast("orderbook_other_oil") *        (1 - Variable("other_international_share"))>
	]
}

# -------------------------------- roro_4000_ceu -------------------------------- #

Copy Vessel "roro_4000_ceu_ice_ammonia"     "roro_4000_ceu_ice_ammonia_domestic"
Copy Vessel "roro_4000_ceu_ice_methane" 	"roro_4000_ceu_ice_methane_domestic"
Copy Vessel "roro_4000_ceu_ice_methanol"    "roro_4000_ceu_ice_methanol_domestic"
Copy Vessel "roro_4000_ceu_ice_oil" 	    "roro_4000_ceu_ice_oil_domestic"

Copy Route "operational_profile_roro_4000_ceu"   "operational_profile_roro_4000_ceu_domestic"

Vessel "roro_4000_ceu_*_domestic" {
	Route = Route("operational_profile_roro_4000_ceu_domestic")
}

Fleet "roro_4000_ceu_domestic" {

	Vessels = [
		Vessel("roro_4000_ceu_ice_ammonia_domestic"),
		Vessel("roro_4000_ceu_ice_methane_domestic"),
		Vessel("roro_4000_ceu_ice_methanol_domestic"),
	    Vessel("roro_4000_ceu_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_roro_4000_ceu") * (1 - Variable("roro_4000_ceu_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_roro_4000_ceu_ammonia") *    (1 - Variable("roro_4000_ceu_international_share"))>,
		<Forecast("orderbook_roro_4000_ceu_methane") * (1 - Variable("roro_4000_ceu_international_share"))>,
		<Forecast("orderbook_roro_4000_ceu_methanol") *   (1 - Variable("roro_4000_ceu_international_share"))>,
	    <Forecast("orderbook_roro_4000_ceu_oil") *        (1 - Variable("roro_4000_ceu_international_share"))>
	]
}

# -------------------------------- roro_7000_ceu -------------------------------- #

Copy Vessel "roro_7000_ceu_ice_ammonia" 	"roro_7000_ceu_ice_ammonia_domestic"
Copy Vessel "roro_7000_ceu_ice_methane"  "roro_7000_ceu_ice_methane_domestic"
Copy Vessel "roro_7000_ceu_ice_methanol" 	"roro_7000_ceu_ice_methanol_domestic"
Copy Vessel "roro_7000_ceu_ice_oil" 		"roro_7000_ceu_ice_oil_domestic"

Copy Route "operational_profile_roro_7000_ceu"   "operational_profile_roro_7000_ceu_domestic"

Vessel "roro_7000_ceu_*_domestic" {
	Route = Route("operational_profile_roro_7000_ceu_domestic")
}

Fleet "roro_7000_ceu_domestic" {

	Vessels = [
		Vessel("roro_7000_ceu_ice_ammonia_domestic"),
		Vessel("roro_7000_ceu_ice_methane_domestic"),
		Vessel("roro_7000_ceu_ice_methanol_domestic"),
	    Vessel("roro_7000_ceu_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_roro_7000_ceu") * (1 - Variable("roro_7000_ceu_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_roro_7000_ceu_ammonia") *    (1 - Variable("roro_7000_ceu_international_share"))>,
		<Forecast("orderbook_roro_7000_ceu_methane") * (1 - Variable("roro_7000_ceu_international_share"))>,
		<Forecast("orderbook_roro_7000_ceu_methanol") *   (1 - Variable("roro_7000_ceu_international_share"))>,
	    <Forecast("orderbook_roro_7000_ceu_oil") *        (1 - Variable("roro_7000_ceu_international_share"))>
	]
}

# -------------------------------- tanker_7500_dwt -------------------------------- #

Copy Vessel "tanker_7500_dwt_ice_ammonia" 	 "tanker_7500_dwt_ice_ammonia_domestic"
Copy Vessel "tanker_7500_dwt_ice_methane" "tanker_7500_dwt_ice_methane_domestic"
Copy Vessel "tanker_7500_dwt_ice_methanol"   "tanker_7500_dwt_ice_methanol_domestic"
Copy Vessel "tanker_7500_dwt_ice_oil" 		 "tanker_7500_dwt_ice_oil_domestic"

Copy Route "operational_profile_tanker_7500_dwt"   "operational_profile_tanker_7500_dwt_domestic"

Vessel "tanker_7500_dwt_*_domestic" {
	Route = Route("operational_profile_tanker_7500_dwt_domestic")
}

Fleet "tanker_7500_dwt_domestic" {

	Vessels = [
		Vessel("tanker_7500_dwt_ice_ammonia_domestic"),
		Vessel("tanker_7500_dwt_ice_methane_domestic"),
		Vessel("tanker_7500_dwt_ice_methanol_domestic"),
	    Vessel("tanker_7500_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_tanker_7500_dwt") * (1 - Variable("tanker_7500_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_tanker_7500_dwt_ammonia") *    (1 - Variable("tanker_7500_dwt_international_share"))>,
		<Forecast("orderbook_tanker_7500_dwt_methane") * (1 - Variable("tanker_7500_dwt_international_share"))>,
		<Forecast("orderbook_tanker_7500_dwt_methanol") *   (1 - Variable("tanker_7500_dwt_international_share"))>,
	    <Forecast("orderbook_tanker_7500_dwt_oil") *        (1 - Variable("tanker_7500_dwt_international_share"))>
	]
}

# -------------------------------- tanker_47k_dwt -------------------------------- #

Copy Vessel "tanker_47k_dwt_ice_ammonia" 	"tanker_47k_dwt_ice_ammonia_domestic"
Copy Vessel "tanker_47k_dwt_ice_methane" "tanker_47k_dwt_ice_methane_domestic"
Copy Vessel "tanker_47k_dwt_ice_methanol" 	"tanker_47k_dwt_ice_methanol_domestic"
Copy Vessel "tanker_47k_dwt_ice_oil" 		"tanker_47k_dwt_ice_oil_domestic"

Copy Route "operational_profile_tanker_47k_dwt"   "operational_profile_tanker_47k_dwt_domestic"

Vessel "tanker_47k_dwt_*_domestic" {
	Route = Route("operational_profile_tanker_47k_dwt_domestic")
}

Fleet "tanker_47k_dwt_domestic" {

	Vessels = [
		Vessel("tanker_47k_dwt_ice_ammonia_domestic"),
		Vessel("tanker_47k_dwt_ice_methane_domestic"),
		Vessel("tanker_47k_dwt_ice_methanol_domestic"),
	    Vessel("tanker_47k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_tanker_47k_dwt") * (1 - Variable("tanker_47k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_tanker_47k_dwt_ammonia") *    (1 - Variable("tanker_47k_dwt_international_share"))>,
		<Forecast("orderbook_tanker_47k_dwt_methane") * (1 - Variable("tanker_47k_dwt_international_share"))>,
		<Forecast("orderbook_tanker_47k_dwt_methanol") *   (1 - Variable("tanker_47k_dwt_international_share"))>,
	    <Forecast("orderbook_tanker_47k_dwt_oil") *        (1 - Variable("tanker_47k_dwt_international_share"))>
	]
}

# -------------------------------- tanker_127k_dwt -------------------------------- #

Copy Vessel "tanker_127k_dwt_ice_ammonia" 	 "tanker_127k_dwt_ice_ammonia_domestic"
Copy Vessel "tanker_127k_dwt_ice_methane" "tanker_127k_dwt_ice_methane_domestic"
Copy Vessel "tanker_127k_dwt_ice_methanol" 	 "tanker_127k_dwt_ice_methanol_domestic"
Copy Vessel "tanker_127k_dwt_ice_oil" 		 "tanker_127k_dwt_ice_oil_domestic"

Copy Route "operational_profile_tanker_127k_dwt"   "operational_profile_tanker_127k_dwt_domestic"

Vessel "tanker_127k_dwt_*_domestic" {
	Route = Route("operational_profile_tanker_127k_dwt_domestic")
}

Fleet "tanker_127k_dwt_domestic" {

	Vessels = [
		Vessel("tanker_127k_dwt_ice_ammonia_domestic"),
		Vessel("tanker_127k_dwt_ice_methane_domestic"),
		Vessel("tanker_127k_dwt_ice_methanol_domestic"),
	    Vessel("tanker_127k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_tanker_127k_dwt") * (1 - Variable("tanker_127k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_tanker_127k_dwt_ammonia") *    (1 - Variable("tanker_127k_dwt_international_share"))>,
		<Forecast("orderbook_tanker_127k_dwt_methane") * (1 - Variable("tanker_127k_dwt_international_share"))>,
		<Forecast("orderbook_tanker_127k_dwt_methanol") *   (1 - Variable("tanker_127k_dwt_international_share"))>,
	    <Forecast("orderbook_tanker_127k_dwt_oil") *        (1 - Variable("tanker_127k_dwt_international_share"))>
	]
}


# -------------------------------- tanker_300k_dwt -------------------------------- #

Copy Vessel "tanker_300k_dwt_ice_ammonia" 	 "tanker_300k_dwt_ice_ammonia_domestic"
Copy Vessel "tanker_300k_dwt_ice_methane" "tanker_300k_dwt_ice_methane_domestic"
Copy Vessel "tanker_300k_dwt_ice_methanol" 	 "tanker_300k_dwt_ice_methanol_domestic"
Copy Vessel "tanker_300k_dwt_ice_oil" 		 "tanker_300k_dwt_ice_oil_domestic"

Copy Route "operational_profile_tanker_300k_dwt"   "operational_profile_tanker_300k_dwt_domestic"

Vessel "tanker_300k_dwt_*_domestic" {
	Route = Route("operational_profile_tanker_300k_dwt_domestic")
}

Fleet "tanker_300k_dwt_domestic" {

	Vessels = [
		Vessel("tanker_300k_dwt_ice_ammonia_domestic"),
		Vessel("tanker_300k_dwt_ice_methane_domestic"),
		Vessel("tanker_300k_dwt_ice_methanol_domestic"),
	    Vessel("tanker_300k_dwt_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_tanker_300k_dwt") * (1 - Variable("tanker_300k_dwt_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_tanker_300k_dwt_ammonia") *    (1 - Variable("tanker_300k_dwt_international_share"))>,
		<Forecast("orderbook_tanker_300k_dwt_methane") * (1 - Variable("tanker_300k_dwt_international_share"))>,
		<Forecast("orderbook_tanker_300k_dwt_methanol") *   (1 - Variable("tanker_300k_dwt_international_share"))>,
	    <Forecast("orderbook_tanker_300k_dwt_oil") *        (1 - Variable("tanker_300k_dwt_international_share"))>
	]
}

# -------------------------------- tug -------------------------------- #

Copy Vessel "tug_ice_ammonia" 	    "tug_ice_ammonia_domestic"
Copy Vessel "tug_ice_methane" 	"tug_ice_methane_domestic"
Copy Vessel "tug_ice_methanol" 	    "tug_ice_methanol_domestic"
Copy Vessel "tug_ice_oil" 		    "tug_ice_oil_domestic"

Copy Route "operational_profile_tug"   "operational_profile_tug_domestic"

Vessel "tug_*_domestic" {
	Route = Route("operational_profile_tug_domestic")
}

Fleet "tug_domestic" {

	Vessels = [
		Vessel("tug_ice_ammonia_domestic"),
		Vessel("tug_ice_methane_domestic"),
		Vessel("tug_ice_methanol_domestic"),
	    Vessel("tug_ice_oil_domestic")
	]

	InitialVessels = <Variable("initial_vessels_tug") * (1 - Variable("tug_international_share"))>

	Orderbooks = [
		<Forecast("orderbook_tug_ammonia") *    (1 - Variable("tug_international_share"))>,
		<Forecast("orderbook_tug_methane") * (1 - Variable("tug_international_share"))>,
		<Forecast("orderbook_tug_methanol") *   (1 - Variable("tug_international_share"))>,
	    <Forecast("orderbook_tug_oil") *        (1 - Variable("tug_international_share"))>
	]
}
