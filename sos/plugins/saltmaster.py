# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin, DebianPlugin


class SaltMaster(Plugin, RedHatPlugin, DebianPlugin):
    """Salt Master
    """

    plugin_name = 'saltmaster'
    profiles = ('sysmgmt',)

    packages = ('salt-master',)

    def setup(self):
        self.add_copy_spec("/var/log/salt/master")
        self.add_cmd_output("salt-key --list all")

# vim: set et ts=4 sw=4 :
