# Copyright (C) 2011, 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import Plugin, IndependentPlugin


class Infiniband(Plugin, IndependentPlugin):

    short_desc = 'Infiniband information'

    plugin_name = 'infiniband'
    profiles = ('hardware',)
    packages = ('libibverbs-utils', 'opensm', 'rdma', 'infiniband-diags')

    def setup(self):
        self.add_copy_spec([
            "/etc/ofed/openib.conf",
            "/etc/ofed/opensm.conf",
            "/etc/rdma"
        ])

        self.add_copy_spec("/var/log/opensm*")

        self.add_cmd_output([
            "ibv_devices",
            "ibv_devinfo -v",
            "ibstat",
            "ibstatus",
            "ibswitches"
        ])

        # run below commands for every IB device and its active port
        ports_cmds = [
            "ibhosts",
            "iblinkinfo",
            "sminfo",
            "perfquery"
        ]
        ib_sysdir = "/sys/class/infiniband/"
        ib_devs = self.listdir(ib_sysdir) if self.path_isdir(ib_sysdir) else []
        for ibdev in ib_devs:
            # Skip OPA hardware, as infiniband-diags tools does not understand
            # OPA specific MAD sent by opa-fm. Intel provides OPA specific
            # tools for OPA fabric diagnose.
            if ibdev.startswith("hfi"):
                continue

            for port in self.listdir(ib_sysdir + ibdev + "/ports"):
                # skip IWARP and RoCE devices
                lfile = ib_sysdir + ibdev + "/ports/" + port + "/link_layer"
                try:
                    with open(lfile, 'r', encoding='UTF-8') as link_fp:
                        link_layer = link_fp.readline()
                        if link_layer != "InfiniBand\n":
                            continue
                except IOError:
                    continue

                sfile = ib_sysdir + ibdev + "/ports/" + port + "/state"
                try:
                    with open(sfile, 'r', encoding='UTF-8') as state_fp:
                        state = state_fp.readline()
                        if not state.endswith(": ACTIVE\n"):
                            continue
                except IOError:
                    continue

                opts = f"-C {ibdev} -P {port}"
                self.add_cmd_output([f"{c} {opts}" for c in ports_cmds])

# vim: set et ts=4 sw=4 :
