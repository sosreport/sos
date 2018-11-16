# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin, UbuntuPlugin


class Services(Plugin, DebianPlugin, UbuntuPlugin):
    """System services
    """

    plugin_name = "services"
    profiles = ('system', 'boot')

    def setup(self):
        self.add_copy_spec([
            "/etc/inittab",
            "/etc/rc.d",
            "/etc/rc*.d"
        ])
        self.add_cmd_output([
            "/sbin/runlevel",
            "ls /var/lock/subsys",
            "service --status-all"
        ])


class RedHatServices(Services, RedHatPlugin):

    def setup(self):
        super(RedHatServices, self).setup()
        self.add_cmd_output("/sbin/chkconfig --list", root_symlink="chkconfig")


# vim: set et ts=4 sw=4 :
