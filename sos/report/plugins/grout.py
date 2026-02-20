# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

import re

from sos.report.plugins import IndependentPlugin, Plugin


class Grout(Plugin, IndependentPlugin):

    short_desc = "Grout graph router"
    plugin_name = "grout"
    profiles = ("network",)
    packages = ("grout",)
    containers = ("grout.*",)

    def setup(self):
        grcli_cmds = [
            "grcli interface",
            "grcli interface stats",
            "grcli address",
            "grcli route",
            "grcli nexthop",
            "grcli nexthop config",
            "grcli stats software",
            "grcli stats hardware",
            "grcli affinity cpus",
            "grcli affinity qmap",
            "grcli fdb",
            "grcli fdb config",
            "grcli flood vtep",
            "grcli conntrack",
            "grcli conntrack config",
            "grcli dnat44",
            "grcli snat44",
            "grcli dhcp",
            "grcli router-advert",
            "grcli srv6 tunsrc",
        ]
        ip_cmds = [
            "ip -d address",
            "ip -d link",
            "ip -4 route",
            "ip -6 route",
        ]

        con = self.get_container_by_name(self.containers[0])

        self.add_cmd_output(grcli_cmds, container=con)

        if con:
            self.add_cmd_output(ip_cmds, container=con)
            self.add_container_logs(list(self.containers))
        else:
            self.add_copy_spec(["/etc/grout.init", "/etc/default/grout"])
            self._collect_netns_ip(ip_cmds)
            self.add_journal(units="grout")

    def _collect_netns_ip(self, ip_cmds):
        """Collect iproute2 info from grout's private network namespace.

        When grout runs as a systemd service with PrivateNetwork=true,
        its netns is unnamed and only reachable via nsenter on the
        daemon PID.
        """
        res = self.collect_cmd_output("systemctl show -p MainPID grout")
        for m in re.finditer(r"MainPID=(\d+)", res["output"]):
            pid = m[0]
            if pid == "0":
                continue
            cmds = [f"nsenter --net -t {pid} {cmd}" for cmd in ip_cmds]
            self.add_cmd_output(cmds)


# vim: set et ts=4 sw=4 :
