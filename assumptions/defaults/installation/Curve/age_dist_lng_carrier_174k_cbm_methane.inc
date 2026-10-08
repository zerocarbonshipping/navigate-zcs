# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GENERATED FILE — DO NOT EDIT.
# Source record: assumptions/vessels/lng_carrier_174k_cbm_fleet_age_distribution.yaml
# Repository: https://github.com/zerocarbonshipping/assumptions
# Tier 2 | status: provisional | provenance: derived | unit: fraction of vessels by age (values_by_x); value = mean age in years (convenience scalar, not bound)
# Share of the LNG carrier fleet by age in whole years at the start of 2025, for the Fleet.InitialAgeDistribution of the methane-fuelled vessel type of lng_carrier_174k_cbm. Derived by counting the methane-burning carriers (FSRUs, FSUs and the slow-speed-diesel ships excluded) in the per-vessel end-2024 fleet table of the IGU World LNG Report 2025 by delivery year. Tier 2: mechanical counting of a public table (script below); the mapping (FSRU/FSU dropped, all propulsion types pooled) needs the Tier 2 first sign-off.

# x = age in years at 1 January 2025
Curve "age_dist_lng_carrier_174k_cbm_methane" {
	Table = [
		0		0.101
		1		0.05
		2		0.042
		3		0.085
		4		0.052
		5		0.061
		6		0.072
		7		0.038
		8		0.042
		9		0.039
		10		0.044
		11		0.024
		12		0.003
		13		0.017
		14		0.024
		15		0.031
		16		0.046
		17		0.041
		18		0.041
		19		0.025
		20		0.028
		21		0.02
		22		0.009
		23		0.002
		24		0.016
		25		0.006
		26		0.006
		27		0.006
		28		0.009
		29		0.005
		30		0.008
		31		0
		32		0
		33		0
		34		0.002
		35		0.002
		36		0
		37		0
		38		0
		39		0
		40		0
		41		0
		42		0
		43		0
		44		0
		45		0
		46		0
		47		0.002
	]
	Extrapolate = FLAT
}
