# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import DebianPlugin, Plugin, RedHatPlugin, UbuntuPlugin


class Grout(Plugin):

    short_desc = "Grout graph router"
    plugin_name = "grout"
    profiles = ("network",)
    packages = ("grout",)
    containers = ("grout.*",)

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

    def setup(self):
        con = self.get_container_by_name(self.containers[0])

        self.add_cmd_output(self.grcli_cmds, container=con)

        if con:
            self.add_cmd_output(self.ip_cmds, container=con)
            self.add_container_logs(list(self.containers))
        else:
            self.add_copy_spec(["/etc/grout.init", "/etc/default/grout"])
            self._collect_netns_ip()
            self.add_journal(units="grout")

    def _collect_netns_ip(self):
        """Collect iproute2 info from grout's private network namespace.

        When grout runs as a systemd service with PrivateNetwork=true,
        its netns is unnamed and only reachable via nsenter on the
        daemon PID.
        """
        res = self.collect_cmd_output("systemctl show -p MainPID grout")
        if res["status"] != 0:
            return
        for line in res["output"].splitlines():
            if line.startswith("MainPID="):
                pid = line.split("=", 1)[1].strip()
                break
        else:
            return
        if not pid or pid == "0":
            return

        self.add_cmd_output(
            [f"nsenter --net -t {pid} {cmd}" for cmd in self.ip_cmds],
        )


class RedHatGrout(Grout, RedHatPlugin):
    pass


class DebianGrout(Grout, DebianPlugin, UbuntuPlugin):
    pass
