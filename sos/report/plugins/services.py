# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.report.plugins import (Plugin, RedHatPlugin, DebianPlugin,
                                UbuntuPlugin, PluginOpt)


class Services(Plugin):

    short_desc = 'System services'

    plugin_name = "services"
    profiles = ('system', 'boot')

    option_list = [
        PluginOpt('servicestatus', default=False,
                  desc='collect status of all running services')
    ]

    def setup(self):
        self.add_copy_spec([
            "/etc/inittab",
            "/etc/rc.d",
            "/etc/rc.local"
        ])
        if self.get_option('servicestatus'):
            self.add_cmd_output("service --status-all")
        self.add_cmd_output([
            "/sbin/runlevel",
            "ls /var/lock/subsys"
        ])


class RedHatServices(Services, RedHatPlugin):

    def setup(self):
        super(RedHatServices, self).setup()
        self.add_cmd_output("/sbin/chkconfig --list", root_symlink="chkconfig")


class DebianServices(Services, DebianPlugin, UbuntuPlugin):

    def setup(self):
        super(DebianServices, self).setup()
        self.add_copy_spec("/etc/rc*.d")

# vim: set et ts=4 sw=4 :
