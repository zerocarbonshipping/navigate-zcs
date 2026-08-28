# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Domain-entity display labels and colour palettes used across the plots.

Maps model entity names / fuel types to their human-readable labels and plot
colours. Rendering configuration (fonts, save/legend options, matplotlib setup)
lives in :mod:`navigate.output.plots._style`.
"""

import numpy as np

from navigate.core.enum_ import FuelTypeID
from navigate.output.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_GREY,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
)

FLEET_LABEL = {
    'tanker_7500_dwt':       'Tanker 7.5K DWT',
    'tanker_47k_dwt':        'Tanker 47K DWT',
    'tanker_127k_dwt':       'Tanker 127K DWT',
    'tanker_300k_dwt':       'Tanker 300K DWT',
    'container_3500_teu':    'Container 3500 TEU',
    'container_8000_teu':    'Container 8000 TEU',
    'container_15000_teu':   'Container 15000 TEU',
    'container_20000_teu':   'Container 20000 TEU',
    'bulk_carrier_26k_dwt':  'Bulk Carrier 26K DWT',
    'bulk_carrier_52k_dwt':  'Bulk Carrier 52K DWT',
    'bulk_carrier_80k_dwt':  'Bulk Carrier 80K DWT',
    'bulk_carrier_200k_dwt': 'Bulk Carrier 200K DWT',
    'cruise_25k_gt':         'Cruise 25K GT',
    'cruise_100k_gt':        'Cruise 100K GT',
    'cruise_175k_gt':        'Cruise 175K GT',
    'gas_carrier_100k_cbm':  'Gas Carrier 100K CBM',
    'roro_4000_ceu':         'Roll-on/Roll-off 4000 CEU',
    'roro_7000_ceu':         'Roll-on/Roll-off 7000 CEU',
    'ferry':                 'Ferry',
    'general_cargo':         'General Cargo 10K DWT',
    'tug':                   'Tug',
    'offshore':              'Offshore',
    'other':                 'Other'
}


FUEL_TYPE_LABEL = {
    FuelTypeID.AMMONIA:     'Ammonia',
    FuelTypeID.ELECTRICITY: 'Electricity',
    FuelTypeID.HYDROGEN:    'Hydrogen',
    FuelTypeID.LPG:         'LPG',
    FuelTypeID.METHANE:     'Methane',
    FuelTypeID.METHANOL:    'Methanol',
    FuelTypeID.OIL:         'Oil'
}


FUEL_TYPE_COLOR = {
    FuelTypeID.AMMONIA:      CENTER_COLORS_BLUE[4],
    FuelTypeID.ELECTRICITY:  CENTER_COLORS_GREEN[3],
    FuelTypeID.HYDROGEN:     CENTER_COLORS_YELLOW[5],
    FuelTypeID.LPG:          CENTER_COLORS_GREY[4],
    FuelTypeID.METHANE:      CENTER_COLORS_RED[4],
    FuelTypeID.METHANOL:     CENTER_COLORS_GREEN[4],
    FuelTypeID.OIL:          CENTER_COLORS_GREY[5]
}


# Canonical fuel-type stacking / grouping order: fossil fuels first, then the
# green fuels, with hydrogen and electricity last. Used by every plot that stacks
# or groups by fuel type.
FUEL_TYPE_ORDER = (
    FuelTypeID.OIL,
    FuelTypeID.LPG,
    FuelTypeID.METHANE,
    FuelTypeID.METHANOL,
    FuelTypeID.AMMONIA,
    FuelTypeID.HYDROGEN,
    FuelTypeID.ELECTRICITY,
)


FUEL_LABEL = {
    'ammonia_blue':                'Blue ammonia',
    'ammonia_electro':             'e-ammonia',
    'ammonia_grey':                'Grey ammonia',
    'diesel_electro':              'e-diesel',
    'electricity':                 'Electricity',
    'fatty_acid_methyl_ester':     'FAME',
    'liquefied_petroleum_gas':     'LPG',
    'liquefied_natural_gas':       'LNG',
    'heavy_fuel_oil':              'HFO',
    'fossil_fuel_oil':             'Fuel oil',
    'oil_bio':                     'Bio-oil',
    'methane_bio':                 'Bio-methane',
    'methane_electro':             'e-methane',
    'methanol_bio':                'Bio-methanol',
    'methanol_electro':            'e-methanol',
    'ethanol_bio':                 'Bio-ethanol'
}


FUEL_COLOR = {
    'ammonia_blue':               np.array([150., 200., 228.]) / 255.,
    'ammonia_electro':            np.array([110., 164., 154.]) / 255.,
    'ammonia_grey':               np.array([220., 220., 220.]) / 255.,
    'diesel_electro':             np.array([40., 100., 100.]) / 255.,
    'electricity':                CENTER_COLORS_GREEN[1],
    'oil_bio':                    np.array([158., 88., 88.]) / 255.,
    'fatty_acid_methyl_ester':    np.array([250., 200., 194.]) / 255.,
    'liquefied_petroleum_gas':    np.array([140., 140., 140.]) / 255.,
    'liquefied_natural_gas':      np.array([220., 220., 220.]) / 255.,
    'heavy_fuel_oil':             np.array([65., 65., 65.]) / 255.,
    'fossil_fuel_oil':            np.array([65., 65., 65.]) / 255.,
    'methane_bio':                np.array([224, 164., 164.]) / 255.,
    'methane_electro':            np.array([184., 224., 194.]) / 255.,
    'methanol_bio':               np.array([194., 128., 128.]) / 255.,
    'methanol_electro':           np.array([68., 122., 122.]) / 255.,
    'ethanol_bio':                np.array([128., 64., 64.]) / 255.
}


# Canonical stacking order for individual (merged) fuels: fossil first, then bio,
# then blue/electro, with electricity last. Mirrors FUEL_TYPE_ORDER one level down
# and is a subset of the FUEL_LABEL / FUEL_COLOR keys.
FUEL_ORDER = (
    'fossil_fuel_oil',
    'liquefied_petroleum_gas',
    'liquefied_natural_gas',
    'ammonia_grey',
    'fatty_acid_methyl_ester',
    'oil_bio',
    'methanol_bio',
    'ethanol_bio',
    'methane_bio',
    'ammonia_blue',
    'ammonia_electro',
    'methanol_electro',
    'methane_electro',
    'diesel_electro',
    'electricity',
)


FEEDSTOCK_LABEL = {
    'carbon_dioxide_biogenic':              'Biogenic CO$_2$ (PS)',
    'demineralized_water':                  'Dem. water',
    'feedstock_bioethanol_fermentation':    'Fermentation feedstock',
    'feedstock_biomethanol_gasification':   'Gasification feedstock',
    'feedstock_biogas':                     'Biogas feedstock',
    'crude_oil':                            'Crude oil',
    'natural_gas':                          'Natural gas',
    'used_cooking_oil':                     'UCO',
    'methanol_grey':                        'Grey methanol'
}


FEEDSTOCK_COLOR = {
    'carbon_dioxide_biogenic':              CENTER_COLORS_GREEN[3],
    'demineralized_water':                  CENTER_COLORS_BLUE[2],
    'feedstock_bioethanol_fermentation':    np.array([194., 128., 128.]) / 255.,
    'feedstock_biomethanol_gasification':   np.array([158., 88., 88.]) / 255.,
    'feedstock_biogas':                     np.array([224., 164., 164.]) / 255.,
    'crude_oil':                            CENTER_COLORS_GREY[5],
    'natural_gas':                          CENTER_COLORS_GREY[3],
    'used_cooking_oil':                     CENTER_COLORS_YELLOW[2],
    'methanol_grey':                        CENTER_COLORS_GREY[3]
}


def extract_label(node, default_dict):
    return default_label(node.name, default_dict)


def default_label(key, default_dict):
    if key in default_dict:
        return default_dict[key]
    else:
        return key
