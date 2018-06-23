# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class Salt(Plugin, RedHatPlugin, DebianPlugin):
    """Salt
    """

    plugin_name = 'salt'
    profiles = ('sysmgmt',)

    packages = ('salt',)

    def setup(self):
        all_logs = self.get_option("all_logs")

        if not all_logs:
            self.add_copy_spec("/var/log/salt/minion")
        else:
            self.add_copy_spec("/var/log/salt")

        self.add_copy_spec("/etc/salt")
        self.add_forbidden_path("/etc/salt/pki/*/*.pem")

# vim: set et ts=4 sw=4 :
