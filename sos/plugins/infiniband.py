# Copyright (C) 2011, 2012 Red Hat, Inc., Bryn M. Reeves <bmr@redhat.com>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Infiniband(Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin):
    """Infiniband data
    """

    plugin_name = 'infiniband'
    profiles = ('hardware',)
    packages = ('libibverbs-utils', 'opensm', 'rdma', 'infiniband-diags')

    def setup(self):
        self.add_copy_spec([
            "/etc/ofed/openib.conf",
            "/etc/ofed/opensm.conf",
            "/etc/rdma"
        ])

        self.add_copy_spec("/var/log/opensm*",
                           sizelimit=self.get_option("log_size"))

        self.add_cmd_output([
            "ibv_devices",
            "ibv_devinfo -v",
            "ibstat",
            "ibstatus"
        ])

        # run below commands for every IB device and its active port
        ports_cmds = [
            "ibhosts",
            "iblinkinfo",
            "sminfo",
            "perfquery"
        ]
        IB_SYS_DIR = "/sys/class/infiniband/"
        ibs = os.listdir(IB_SYS_DIR)
        for ib in ibs:
            """
            Skip OPA hardware, as infiniband-diags tools does not understand
            OPA specific MAD sent by opa-fm. Intel provides OPA specific tools
            for OPA fabric diagnose.
            """
            if ib.startswith("hfi"):
                continue

            for port in os.listdir(IB_SYS_DIR + ib + "/ports"):
                # skip IWARP and RoCE devices
                try:
                    p = open(IB_SYS_DIR + ib + "/ports/" + port +
                             "/link_layer")
                except:
                    continue
                link_layer = p.readline()
                p.close()
                if link_layer != "InfiniBand\n":
                    continue

                try:
                    s = open(IB_SYS_DIR + ib + "/ports/" + port + "/state")
                except:
                    continue
                state = s.readline()
                s.close()

                if not state.endswith(": ACTIVE\n"):
                    continue

                opts = "-C %s -P %s" % (ib, port)
                self.add_cmd_output(["%s %s" % (c, opts) for c in port_cmds])

# vim: set et ts=4 sw=4 :
