# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Cgroups(Plugin, DebianPlugin, UbuntuPlugin):
    """Control groups subsystem
    """

    plugin_name = "cgroups"
    profiles = ('container', 'system')
    files = ('/proc/cgroups',)

    def setup(self):
        self.add_copy_spec([
            "/proc/cgroups",
            "/sys/fs/cgroup"
        ])

        self.add_cmd_output("systemd-cgls")

        return


class RedHatCgroups(Cgroups, RedHatPlugin):

    def setup(self):
        super(RedHatCgroups, self).setup()
        self.add_copy_spec([
            "/etc/sysconfig/cgconfig",
            "/etc/sysconfig/cgred",
            "/etc/cgsnapshot_blacklist.conf",
            "/etc/cgconfig.conf",
            "/etc/cgrules.conf"
        ])

# vim: set et ts=4 sw=4 :
