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
        IB_SYS_DIR = "/sys/class/infiniband/"
        ibs = self.listdir(IB_SYS_DIR) if self.path_isdir(IB_SYS_DIR) else []
        for ib in ibs:
            """
            Skip OPA hardware, as infiniband-diags tools does not understand
            OPA specific MAD sent by opa-fm. Intel provides OPA specific tools
            for OPA fabric diagnose.
            """
            if ib.startswith("hfi"):
                continue

            for port in self.listdir(IB_SYS_DIR + ib + "/ports"):
                # skip IWARP and RoCE devices
                try:
                    p = open(IB_SYS_DIR + ib + "/ports/" + port +
                             "/link_layer")
                except IOError:
                    continue
                link_layer = p.readline()
                p.close()
                if link_layer != "InfiniBand\n":
                    continue

                try:
                    s = open(IB_SYS_DIR + ib + "/ports/" + port + "/state")
                except IOError:
                    continue
                state = s.readline()
                s.close()

                if not state.endswith(": ACTIVE\n"):
                    continue

                opts = "-C %s -P %s" % (ib, port)
                self.add_cmd_output(["%s %s" % (c, opts) for c in ports_cmds])

# vim: set et ts=4 sw=4 :
