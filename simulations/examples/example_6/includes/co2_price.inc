# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GERMANY'S NATIONAL CO2 PRICE on inland waterways, as a copy of the library's
# EU ETS regulation: an absolute price on the CO2-equivalent burned on board,
# no free allowance, biofuels and e-fuels counted as zero CO2. A Regulation, not a
# Levy, so that the price enters the expected costs of the newbuild choice.
# Covers every ship (set_include_vessel is TRUE in the copied regulation; stated
# again below because Navigate's code default is FALSE).
# The coverage fractions are left as in eu_ets: every leg is between two covered
# ports, so IntraFraction = 1 applies throughout.

Copy Regulation "eu_ets" "co2_price_germany"

Regulation "co2_price_germany" {
	# the five ports of the route
	Jurisdiction = [Port("duisburg"), Port("cologne"), Port("koblenz"), Port("mainz"), Port("mannheim")]

	# INVENTED: USD per t CO2, 65 in 2026 to 150 in 2050 (placeholders.inc)
	RemedialCost = Forecast("germany_co2_price")

	set_include_vessel("*", TRUE)
}

Report "report_co2_price_germany" {
	Directory = "./reports"

	add_regulation_property("co2_price_germany", RemedialExpenses)
	add_regulation_property("co2_price_germany", FlexibilityExpenses)
	add_regulation_property("co2_price_germany", SurplusRevenue)
}
