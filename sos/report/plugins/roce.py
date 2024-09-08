# Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES.
# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import shutil
from sos.report.plugins import Plugin, IndependentPlugin


class RoCE(Plugin, IndependentPlugin):

    short_desc = 'RoCE (RDMA over Converged Ethernet) information'

    plugin_name = 'roce'
    profiles = ('hardware',)
    # rdma installed with iproute2
    packages = ('iproute2', 'infiniband-diags')

    def setup(self):

        cma_rocy_installed = shutil.which('cma_roce_mode') is not None

        IB_SYS_DIR = "/sys/class/infiniband/"
        ibs = self.listdir(IB_SYS_DIR) if self.path_isdir(IB_SYS_DIR) else []
        for ib in ibs:

            # cma_roce_mode and cma_roce_tos will not work for bond devices
            # ibstat is used to check if the device exist or not, form bond
            # the command will return an erro:
            # stat of IB device <device> failed: No such file or directory
            skip_cma_roce = False
            ibstat_out = self.exec_cmd(f'ibstat -s {ib}')
            if cma_rocy_installed is False or ibstat_out['status'] != 0:
                skip_cma_roce = True

            # dump ECN configuration

            for port in self.listdir(IB_SYS_DIR + ib + "/ports"):
                # skip Infiniband and IWARP devices
                try:
                    with open(IB_SYS_DIR + ib + "/ports/" + port +
                              "/link_layer") as p:
                        link_layer = p.readline()
                except IOError:
                    continue
                if link_layer != "Ethernet\n":
                    continue

                # dump counters
                roce_counters = IB_SYS_DIR + ib + "/ports/" + port + \
                    "/counters"
                self.add_copy_spec([roce_counters])

                # dump HW counters
                roce_hw_counters = IB_SYS_DIR + ib + "/ports/" + port + \
                    "/hw_counters"
                self.add_copy_spec([roce_hw_counters])

                # dump gids
                gids = IB_SYS_DIR + ib + "/ports/" + port + "/gids"
                self.add_copy_spec([gids])

                # dump gid attributes
                gid_attrs = IB_SYS_DIR + ib + "/ports/" + port + "/gid_attrs"
                self.add_copy_spec([gid_attrs])

                # dump ECN configuration

                netsys = IB_SYS_DIR + ib + "/device/net"
                for netdev in self.listdir(netsys):

                    # dump roce_np
                    roce_np = netsys + "/" + netdev + "/ecn/roce_np"
                    self.add_copy_spec([roce_np])

                    # dump roce_rp
                    roce_rp = netsys + "/" + netdev + "/ecn/roce_rp"
                    self.add_copy_spec([roce_rp])

                if not skip_cma_roce:
                    # cma roce mode
                    self.add_cmd_output([f"cma_roce_mode -d {ib} -p {port}"])

                    # cma roce tos
                    self.add_cmd_output([f"cma_roce_tos -d {ib} -p {port}"])
