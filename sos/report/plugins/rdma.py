# Copyright (C) 2023 Nvidia Corporation, Majd Dibbiny <majd@nvidia.com>
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Rdma(Plugin, IndependentPlugin):

    short_desc = 'RDMA plugin collects status, statistics and resources of all\
    the RDMA devices in the system'

    plugin_name = "rdma"
    profiles = ('hardware',)
    packages = ('iproute2',)

    def setup(self):

        rdma_cmds = [
            "dev show",
            "link show",
            "system show",
            "statistic show"
        ]

        rdma_rsc_obj = [
            "qp",
            "cm_id",
            "cq",
            "pd",
            "mr",
            "ctx",
            "srq"
        ]

        self.add_cmd_output([f"rdma {cmd} -d" for cmd in rdma_cmds])

        self.add_cmd_output([f"rdma resource show {rsc} -d"
                             for rsc in rdma_rsc_obj])
