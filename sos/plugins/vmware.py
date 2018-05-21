# This file is part of the sos project: https://github.com/sosreport/sos
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# version 2 of the GNU General Public License.
#
# See the LICENSE file in the source distribution for further information.

from sos.plugins import Plugin, RedHatPlugin


class VMWare(Plugin, RedHatPlugin):
    """VMWare client information
    """

    plugin_name = 'vmware'
    profiles = ('virt',)

    files = ('vmware', '/usr/init.d/vmware-tools')

    def setup(self):
        self.add_cmd_output("vmware -v")
        self.add_copy_spec([
            "/etc/vmware/locations",
            "/etc/vmware/config",
            "/proc/vmmemctl"
        ])

# vim: set et ts=4 sw=4 :
