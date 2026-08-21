# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, command_assignment_to_dict, command_assignment_to_tuple_dict
from navigate.core.id_ import FORECAST, REGION, TIMETABLE, VARIABLE
from navigate.core.nodes.node import Node


class Region(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = REGION

        # process
        self._process_CAPEX = {}                    # dict[process_name: float], CAPEX of a process, USD/ton
        self._process_OPEX = {}                     # dict[process_name: float], OPEX of a process, USD/ton/year
        self._process_energy = {}                   # dict[process_name: float], energy demand of a process, MWh/ton
        self._process_lifetime = {}                 # dict[process_name: float], lifetime of the process, years
        self._process_replacement = {}              # dict[process_name: float], fraction of CAPEX repaid at EoL
        self._process_WTT = {}                      # dict[(process_name, emission_name): float], ton emission/ton fuel

        # source
        self._source_CAPEX = {}     # dict[source_name: float], CAPEX of a source, USD/MWh (stand-alone)
        self._source_OPEX = {}      # dict[source_name: float], OPEX of a source, USD/MWh/year (stand-alone)
        self._source_WTT = {}       # dict[(source_name, emission_name): float], ton emission/MWh

        # feedstock
        self._feedstock_cost = {}   # dict[feedstock_name: float], cost of a feedstock, USD/ton
        self._feedstock_WTT = {}    # dict[(feedstock_name, emission_name): float], ton emission/ton fuel

        # transport
        self._transport_cost = {}   # dict[transport_name: float], cost of a transport, USD/ton-nautical mile
        self._transport_WTT = {}    # dict[(transport_name, emission_name): float], ton emission/ton-nautical mile

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_process_capex(self, process_name, value):
        """
        Set the CAPEX associated with a production process in USD/ton.

        Examples
        --------
        - "process_name", 500
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name : str
            The name of a process.
        value : float | NodeReference
            The CAPEX cost of the process in USD/ton.
        """

        command_assignment_to_dict(process_name, value, self._process_CAPEX, type_=(FORECAST, TIMETABLE, VARIABLE),
                                   lower=0.)

    def set_process_opex(self, process_name, value):
        """
        Set the OPEX associated with a production process in USD/ton/year.

        Notice that OPEX allows negative values so that revenue from byproducts can be subtracted from the costs,
        resulting in potentially negative OPEX.

        Examples
        --------
        - "process_name", 50
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name : str
            The name of a process.
        value : float | NodeReference
            The OPEX cost of the process in USD/ton/year.
        """

        command_assignment_to_dict(process_name, value, self._process_OPEX, type_=(FORECAST, TIMETABLE, VARIABLE))

    def set_process_energy(self, process_name, value):
        """
        Set the energy demand required to run a production process in MWh/ton.

        Examples
        --------
        - "process_name", 3.7
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name : str
            The name of a process.
        value : float | NodeReference
            The energy demand of the process in MWh/ton.
        """

        command_assignment_to_dict(process_name, value, self._process_energy, type_=(FORECAST, VARIABLE), lower=0.)

    def set_process_lifetime(self, process_name, value):
        """
        Set the lifetime of a production process in years.

        Examples
        --------
        - "process_name", 25
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name : str
            The name of a process.
        value : float | NodeReference
            The lifetime of the process in years.
        """

        command_assignment_to_dict(process_name, value, self._process_lifetime, type_=(FORECAST, VARIABLE), lower=0.)

    def set_process_replacement(self, process_name, value):
        """
        Set the replacement fraction of CAPEX repaid at the end of a process's lifetime.

        Examples
        --------
        - "process_name", 0.5
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name : str
            The name of a process.
        value : float | NodeReference
            The replacement fraction of the CAPEX repaid at EoL (end of lifetime).
        """

        command_assignment_to_dict(process_name, value, self._process_replacement, type_=(FORECAST, VARIABLE),
                                   lower=0., upper=1.)

    def set_process_wtt(self, process_name, emission_name, value):
        """
        Set the WTT emissions of a specific emission type emitted during a production process in ton emission/ton fuel.

        Examples
        --------
        - "process_name", "emission_name",  0.5
        - "process_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        process_name : str
            The name of a process.
        emission_name : str
            The name of an emission.
        value : float | NodeReference
            The amount of emissions emitted during the production in ton emissions/ton fuel.
        """

        command_assignment_to_tuple_dict((process_name, emission_name), value, self._process_WTT,
                                         type_=(FORECAST, VARIABLE))

    def set_source_capex(self, source_name, value):
        """
        Set the CAPEX associated with a source in USD/MWh.

        Examples
        --------
        - "source_name", 50
        - "source_name", Forecast("name")

        Parameters
        ----------
        source_name : str
            The name of a source.
        value : float | NodeReference
            The CAPEX cost of the source in USD/MWh.
        """

        command_assignment_to_dict(source_name, value, self._source_CAPEX, type_=(FORECAST, VARIABLE), lower=0.)

    def set_source_opex(self, source_name, value):
        """
        Set the OPEX associated with a source in USD/MWh/year.

        Examples
        --------
        - "source_name", 50
        - "source_name", Forecast("name")

        Parameters
        ----------
        source_name : str
            The name of a source.
        value : float | NodeReference
            The OPEX cost of the source in USD/MWh/year.
        """

        command_assignment_to_dict(source_name, value, self._source_OPEX, type_=(FORECAST, VARIABLE), lower=0.)

    def set_source_wtt(self, source_name, emission_name, value):
        """
        Set the WTT emissions of a specific emission type emitted by using a source in ton emission/MWh.

        Examples
        --------
        - "source_name", "emission_name",  0.5
        - "source_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        source_name : str
            The name of a source.
        emission_name : str
            The name of an emission.
        value : float | NodeReference
            The amount of emissions emitted by using a source in ton emission/MWh.
        """

        command_assignment_to_tuple_dict((source_name, emission_name), value, self._source_WTT,
                                         type_=(FORECAST, VARIABLE))

    def set_feedstock_cost(self, feedstock_name, value):
        """
        Set the cost of a feedstock in USD/ton.

        Examples
        --------
        - "feedstock_name", 150
        - "feedstock_name", Forecast("name")

        Parameters
        ----------
        feedstock_name : str
            The name of a feedstock.
        value : float | NodeReference
            The cost of a feedstock in USD/ton.
        """

        command_assignment_to_dict(feedstock_name, value, self._feedstock_cost, type_=(FORECAST, VARIABLE), lower=0.)

    def set_feedstock_wtt(self, feedstock_name, emission_name, value):
        """
        Set the WTT emissions of a specific emission emitted by using a feedstock in ton emission/ton feedstock.

        Examples
        --------
        - "feedstock_name", "emission_name",  0.5
        - "feedstock_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        feedstock_name : str
            The name of a feedstock.
        emission_name : str
            The name of an emission.
        value : float | NodeReference
            The amount of emissions emitted by using a feedstock in ton emission/ton feedstock.
        """

        command_assignment_to_tuple_dict((feedstock_name, emission_name),
                                         value,
                                         self._feedstock_WTT,
                                         type_=(FORECAST, VARIABLE))

    def set_transport_cost(self, transport_name, value):
        """
        Set the cost associated with a transport in USD/ton-nautical mile.

        Examples
        --------
        - "transport_name", 45
        - "transport_name", Forecast("name")

        Parameters
        ----------
        transport_name : str
            The name of a transport.
        value : float | NodeReference
            The cost of the transport in USD/MWh.
        """

        command_assignment_to_dict(transport_name, value, self._transport_cost, type_=(FORECAST, VARIABLE), lower=0.)

    def set_transport_wtt(self, transport_name, emission_name, value):
        """
        Set the WTT emissions of a specific emission emitted by using a transport in ton emission/ton-nautical mile.

        Examples
        --------
        - "transport_name", "emission_name",  0.5
        - "transport_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        transport_name : str
            The name of a transport.
        emission_name : str
            The name of an emission.
        value : float | NodeReference
            The amount of emissions emitted by using a transport in ton emission/ton-nautical mile.
        """

        command_assignment_to_tuple_dict((transport_name, emission_name),
                                         value,
                                         self._transport_WTT,
                                         type_=(FORECAST, VARIABLE))

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        for process_name in self._process_CAPEX:

            if not self._process_CAPEX[process_name]:
                self._process_CAPEX[process_name] = Scalar(0.)

            if not self._process_OPEX[process_name]:
                self._process_OPEX[process_name] = Scalar(0.)

            if not self._process_energy[process_name]:
                self._process_energy[process_name] = Scalar(0.)

            if not self._process_replacement[process_name]:
                self._process_replacement[process_name] = Scalar(0.)

        for (process_name, emission_name) in self._process_WTT:
            if not self._process_WTT[(process_name, emission_name)]:
                self._process_WTT[(process_name, emission_name)] = Scalar(0.)

        for feedstock_name in self._feedstock_cost:
            if not self._feedstock_cost[feedstock_name]:
                self._feedstock_cost[feedstock_name] = Scalar(0.)

        for (feedstock_name, emission_name) in self._feedstock_WTT:
            if not self._feedstock_WTT[(feedstock_name, emission_name)]:
                self._feedstock_WTT[(feedstock_name, emission_name)] = Scalar(0.)

        for source_name in self._source_CAPEX:
            if not self._source_CAPEX[source_name]:
                self._source_CAPEX[source_name] = Scalar(0.)

        for source_name in self._source_OPEX:
            if not self._source_OPEX[source_name]:
                self._source_OPEX[source_name] = Scalar(0.)

        for (source_name, emission_name) in self._source_WTT:
            if not self._source_WTT[(source_name, emission_name)]:
                self._source_WTT[(source_name, emission_name)] = Scalar(0.)

        for transport_name in self._transport_cost:
            if not self._transport_cost[transport_name]:
                self._transport_cost[transport_name] = Scalar(0.)

        for (transport_name, emission_name) in self._transport_WTT:
            if not self._transport_WTT[(transport_name, emission_name)]:
                self._transport_WTT[(transport_name, emission_name)] = Scalar(0.)

    def initialize_dependencies(self, emissions, feedstocks, processes, sources, transports):
        """
        Initialize all dependent dictionaries.

        Parameters
        ----------
        emissions : dict[str, Emission]
            All emissions in the simulation.
        feedstocks : dict[str, Feedstock]
            All feedstocks in the simulation.
        processes : dict[str, Process]
            All processes in the simulation.
        sources : dict[str, Source]
            All sources in the simulation.
        transports : dict[str, Transport]
            All transports in the simulation.
        """

        for process_name in processes:

            self._process_CAPEX.setdefault(process_name, None)
            self._process_OPEX.setdefault(process_name, None)
            self._process_energy.setdefault(process_name, None)
            self._process_lifetime.setdefault(process_name, None)
            self._process_replacement.setdefault(process_name, None)

            for emission_name in emissions:
                self._process_WTT.setdefault((process_name, emission_name), None)

        for feedstock_name in feedstocks:

            self._feedstock_cost.setdefault(feedstock_name, None)

            for emission_name in emissions:
                self._feedstock_WTT.setdefault((feedstock_name, emission_name), None)

        for source_name in sources:

            self._source_CAPEX.setdefault(source_name, None)
            self._source_OPEX.setdefault(source_name, None)

            for emission_name in emissions:
                self._source_WTT.setdefault((source_name, emission_name), None)

        for transport_name in transports:

            self._transport_cost.setdefault(transport_name, None)

            for emission_name in emissions:
                self._transport_WTT.setdefault((transport_name, emission_name), None)

    def get_process_CAPEX(self, process_name):
        return self._process_CAPEX[process_name]

    def get_process_OPEX(self, process_name):
        return self._process_OPEX[process_name]

    def get_process_energy(self, process_name):
        return self._process_energy[process_name]

    def get_process_lifetime(self, process_name):
        return self._process_lifetime[process_name]

    def get_process_replacement(self, process_name):
        return self._process_replacement[process_name]

    def get_process_WTT(self, process_name, emission_name):
        return self._process_WTT[(process_name, emission_name)]

    def get_source_CAPEX(self, source_name):
        return self._source_CAPEX[source_name]

    def get_source_OPEX(self, source_name):
        return self._source_OPEX[source_name]

    def get_source_WTT(self, source_name, emission_name):
        return self._source_WTT[(source_name, emission_name)]

    def get_feedstock_cost(self, feedstock_name):
        return self._feedstock_cost[feedstock_name]

    def get_feedstock_WTT(self, feedstock_name, emission_name):
        return self._feedstock_WTT[(feedstock_name, emission_name)]

    def get_transport_cost(self, source_name):
        return self._transport_cost[source_name]

    def get_transport_WTT(self, transport_name, emission_name):
        return self._transport_WTT[(transport_name, emission_name)]
